"""Disposable geometry worker; a bad coordinate cannot poison later previews."""
import importlib
import importlib.abc
import importlib.util
import json
import sys

from .model import Catalog


class EditedSources(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, sources):
        self.sources = {p[:-3].replace("/", "."): (p, s) for p, s in sources.items()}

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.sources:
            return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        path, source = self.sources[module.__name__]
        exec(compile(source, path, "exec"), module.__dict__)


def outline(g):
    paths = []
    polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    for poly in polys:
        for ring in [poly.exterior, *poly.interiors]:
            coords = list(ring.simplify(0.004).coords)
            paths.append("M" + " L".join(f"{x:.4f},{y:.4f}" for x, y in coords) + " Z")
    return " ".join(paths)


def checks(g):
    from beadjoint.glyphs import pieces
    from beadjoint.verify import check_glyph
    if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("The edit did not produce a valid, nonempty glyph.")
    if max(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1]) > 80:
        raise ValueError("The edit produces an oversized glyph.")
    r = check_glyph(g)
    ps = pieces(g)
    gap = min((a.distance(b) for i, a in enumerate(ps) for b in ps[i + 1:]), default=None)
    r["piece_gap"] = round(gap, 3) if gap is not None else None
    r["ok"] = r["ok"] and (gap is None or gap >= 1.98)
    return r


def run(request):
    from beadjoint import charset, setting
    catalog = Catalog()
    edited = catalog.edited_sources(request["session"])
    family = request.get("family", "P")
    char = request.get("char", "a")
    text = request.get("text", "Hamburgefonts 0123")
    if family not in ("P", "T", "M") or not isinstance(char, str) or len(char) != 1:
        raise ValueError("Choose one glyph and a P, T, or M family.")
    if not isinstance(text, str) or len(text) > 72 or any(ord(c) < 32 for c in text):
        raise ValueError("Preview text must be one line of at most 72 characters.")
    validate = request.get("validate", False) is True

    def families():
        return {"P": charset.full_p, "T": charset.full_mixed, "M": charset.full_m}

    baseline = {f: build() for f, build in families().items() if validate or f == family}
    if char not in baseline[family]:
        raise ValueError(f"{char!r} is not included in this family. Try Proportional.")
    before = baseline[family][char].geom
    if edited:
        finder = EditedSources(edited)
        sys.meta_path.insert(0, finder)
        # All downstream caches and imported constructor aliases are recreated.
        for module in ("geom", "glyphs", "latin", "marks", "charset", "setting"):
            importlib.reload(importlib.import_module("beadjoint." + module))
    after = {f: build() for f, build in families().items() if validate or f == family}
    glyphs = after[family]
    if char not in glyphs:
        raise ValueError("The edit removes this glyph from Mono: its ink must fit the 10w width limit.")
    current = glyphs[char].geom
    result = {"before": outline(before), "after": outline(current), "bounds": list(before.union(current).bounds),
              "checks": checks(current), "width": round(glyphs[char].width, 4), "family": family,
              "changed": [], "failures": [], "validation": validate}
    setter = {"P": setting.kerned, "T": setting.mixed, "M": setting.tabular}[family]
    from beadjoint.verify import line_gaps
    line = setter(text, glyphs)
    result["text_paths"] = [outline(g) for _, g, _ in line]
    result["text_bounds"] = [min(g.bounds[0] for _, g, _ in line), min(g.bounds[1] for _, g, _ in line),
                             max(g.bounds[2] for _, g, _ in line), max(g.bounds[3] for _, g, _ in line)] if line else [0, -4, 10, 10]
    gaps = line_gaps([(c, g) for c, g, _ in line])
    result["text_gap"] = round(min(d for _, _, d in gaps), 3) if gaps else None
    if result["text_gap"] is not None and result["text_gap"] < 1.98:
        result["failures"].append("Preview text has a gap below 1.98w.")
    if validate:
        for f, new in after.items():
            old = baseline[f]
            for c in sorted(old.keys() - new.keys()):
                result["failures"].append(f"{f}:{c} disappeared (Mono width overflow).")
            for c, glyph in new.items():
                if c in old and glyph.geom.equals_exact(old[c].geom, 1e-8):
                    continue
                report = checks(glyph.geom)
                result["changed"].append({"family": f, "char": c, "checks": report})
                if not report["ok"]:
                    result["failures"].append(f"{f}:{c} violates ink, enclosed-gap, or separate-piece checks.")
                if f == "T" and c.isascii() and c.isdigit() and glyph.width > 7.02:
                    result["failures"].append(f"T:{c} exceeds the tabular digit width budget (7w).")
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(run(json.load(sys.stdin)), allow_nan=False))
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        sys.exit(1)
