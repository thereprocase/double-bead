"""Disposable geometry worker; a bad coordinate cannot poison later previews."""
import importlib
import importlib.abc
import importlib.util
import json
import sys
from collections.abc import Mapping

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


# Finishing fills negative space narrower than about 2w with ink. Acute joins (v, k, N) are
# filled by design, so only fill an edit adds beyond the original glyph is reported.
FILL_WARN = 0.5  # w², the same size threshold fill_pinches applies to one pinch


class _ReadLog(Mapping):
    """Pass-through view of a glyph dict that remembers every value read from it."""

    def __init__(self, data):
        self.data, self.read = data, []

    def __getitem__(self, key):
        value = self.data[key]
        self.read.append(value)
        return value

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


class FillMeter:
    """Record how much ink fill_pinches adds each time charset finishes a glyph.

    charset binds finish and calls marks.compose by name, and geom.finish calls fill_pinches
    through its module globals, so the wrappers go on the currently loaded modules: create a
    new meter after reloading them. Results are keyed by the finished geometry object, which
    the families store unchanged in their Glyph records. A composite also carries the fill
    of the finished base it was composed from.
    """

    def __init__(self):
        from beadjoint import charset, geom, marks
        self.finished = {}
        real_fill, real_finish, real_compose = geom.fill_pinches, geom.finish, marks.compose
        added, composed = [], {}

        def fill_pinches(g, *args, **kwargs):
            out = real_fill(g, *args, **kwargs)
            added.append(out.area - geom._clean(g).area)
            return out

        def compose(ch, base, marks_, fin, *args, **kwargs):
            # Record the finished glyph compose actually reads: under marks above it swaps
            # i and j for dotless ı and ȷ, so the decomposed base letter is not always used.
            view = _ReadLog(fin)
            out = real_compose(ch, base, marks_, view, *args, **kwargs)
            composed[id(out)] = (out, view.read[0] if view.read else None)
            return out

        def finish(g):
            added.clear()
            out = real_finish(g)
            _, base = composed.pop(id(g), (None, None))
            self.finished[id(out)] = (out, sum(added), base)
            return out

        geom.fill_pinches, marks.compose, charset.finish = fill_pinches, compose, finish

    def filled(self, geom, depth=0):
        """Filled area in w² for a finished glyph, including its base's fill; None if unmetered."""
        record = self.finished.get(id(geom))
        if record is None or depth > 4:
            return None
        _, area, base = record
        base_area = self.filled(base, depth + 1) if base is not None else 0.0
        return area + (base_area or 0.0)


def fill_change(before_meter, before, after_meter, after):
    """(before, after, warn) filled areas for one glyph; unmetered glyphs never warn."""
    a, b = before_meter.filled(before), after_meter.filled(after)
    if a is None or b is None:
        return None, None, False
    return round(a, 2), round(b, 2), b - a > FILL_WARN


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

    before_meter = FillMeter()
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
        after_meter = FillMeter()
    else:
        after_meter = before_meter
    after = {f: build() for f, build in families().items() if validate or f == family}
    glyphs = after[family]
    if char not in glyphs:
        raise ValueError("The edit removes this glyph from Mono: its ink must fit the 10w width limit.")
    current = glyphs[char].geom
    result = {"before": outline(before), "after": outline(current), "bounds": list(before.union(current).bounds),
              "checks": checks(current), "width": round(glyphs[char].width, 4), "family": family,
              "changed": [], "failures": [], "warnings": [], "validation": validate}
    fill_before, fill_after, fill_warn = fill_change(before_meter, before, after_meter, current)
    result["fill"] = {"before": fill_before, "after": fill_after, "warn": fill_warn}
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
                # A glyph that newly fits Mono has no Mono original; every character is in P.
                reference = old.get(c) or baseline["P"].get(c)
                *_, fill_warn = fill_change(before_meter, reference.geom if reference else None, after_meter, glyph.geom)
                result["changed"].append({"family": f, "char": c, "checks": report, "fill_warn": fill_warn})
                if fill_warn:
                    result["warnings"].append(f"{f}:{c}")
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
