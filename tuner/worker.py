"""Disposable geometry worker; a bad coordinate cannot poison later previews.

Reads one preview request as JSON on standard input and prints the result, or
{"error": message, "code": short code} with exit status 1, as JSON.
"""
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
import re
import struct
import sys
import traceback
from pathlib import Path

from .model import ROOT, SOURCE_PATHS, Catalog, TunerError

FAMILY_NAMES = {"P": "Proportional", "T": "Tab", "M": "Mono"}
# Runaway geometry, not a design rule: coordinates stay within ±32w, and check_glyph rasterises
# at 40 px/w, so a larger glyph would only cost time and memory before failing anyway.
MAX_EXTENT = 80.0
MAX_TEXT = 72


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


class Beadjoint:
    """The beadjoint modules one build uses, and the limits the checks take from them.

    After an edit the whole package is imported again from the edited sources, so every limit is
    read from the modules that built the glyphs it judges.
    """

    def __init__(self):
        def load(name):
            return importlib.import_module("beadjoint." + name)

        self.charset, self.setting, self.geom = load("charset"), load("setting"), load("geom")
        self.glyphs, self.marks, self.verify = load("glyphs"), load("marks"), load("verify")
        self.families = {"P": self.charset.full_p, "T": self.charset.full_mixed, "M": self.charset.full_m}
        self.setters = {"P": self.setting.kerned, "T": self.setting.mixed, "M": self.setting.tabular}
        self.line_min = self.verify.LINE_MIN          # least distance between separate pieces of ink
        self.fill_warn = self.geom.PINCH_MIN_AREA     # w²: the size of one pinch that finishing fills
        self.mono_max = self.charset.MONO_MAX         # widest ink Mono keeps
        # Tab centres every digit in a CELL_F cell, so two neighbouring digits keep the line gap
        # only while neither is wider than the cell less that gap (9 - 1.98 = 7.02w).
        self.tab_cell = self.setting.CELL_F
        self.tab_digit = self.setting.CELL_F - self.verify.LINE_MIN

    @staticmethod
    def reload(edited):
        """Import the package again, reading the edited sources instead of the files on disk.

        Every beadjoint module is dropped, not only the edited ones: the others bind names and
        cache glyphs from the modules they imported, and a hand-kept reload order breaks silently
        when a module is added.
        """
        sys.meta_path.insert(0, EditedSources(edited))
        for name in [n for n in sys.modules if n == "beadjoint" or n.startswith("beadjoint.")]:
            del sys.modules[name]
        return Beadjoint()


def outline(g):
    paths = []
    polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    for poly in polys:
        for ring in [poly.exterior, *poly.interiors]:
            coords = list(ring.simplify(0.004).coords)
            paths.append("M" + " L".join(f"{x:.4f},{y:.4f}" for x, y in coords) + " Z")
    return " ".join(paths)


# Set by the server to a private directory that lives as long as it does.
CACHE_ENV = "FILLAPRINT_TUNER_CACHE"
_RECORD = struct.Struct("<32sdI")   # sha256 of the input geometry, pinch-fill area, output size


class FinishedCache:
    """Finished glyphs from earlier workers, keyed by the exact bytes of the input geometry.

    Finishing is a pure function of its input and dominates preview time, so a glyph whose
    input is unchanged is read back instead of finished again. Only glyphs finished from the
    unedited sources are written to disk; edited results stay in this process. The file is
    written by the worker into the server's private directory, and WKB parsing cannot
    execute code; a damaged file is ignored.
    """

    def __init__(self, directory):
        self.path = os.path.join(directory, "finished-v1.bin") if directory else None
        self.entries, self.unsaved, self.volatile = {}, False, set()
        try:
            data = open(self.path, "rb").read() if self.path else b""
            offset = 0
            while offset < len(data):
                key, area, size = _RECORD.unpack_from(data, offset)
                offset += _RECORD.size
                self.entries[key] = (area, data[offset:offset + size])
                offset += size
        except (OSError, struct.error):
            self.entries = {}

    @staticmethod
    def key(geom):
        return hashlib.sha256(geom.wkb).digest()

    def get(self, key):
        return self.entries.get(key)

    def put(self, key, area, wkb, persist):
        self.entries[key] = (area, wkb)
        self.unsaved = self.unsaved or persist
        if not persist:
            self.volatile.add(key)

    def save(self):
        if not (self.path and self.unsaved):
            return
        records = [_RECORD.pack(k, a, len(w)) + w for k, (a, w) in self.entries.items() if k not in self.volatile]
        partial = self.path + ".partial"
        with open(partial, "wb") as f:
            f.write(b"".join(records))
        os.replace(partial, self.path)
        self.unsaved = False


class FillMeter:
    """Record how much ink fill_pinches adds each time charset finishes a glyph.

    charset binds finish and calls marks.compose by name, and geom.finish calls fill_pinches
    through its module globals, so the wrappers go on the modules of one Beadjoint: create a
    new meter for the modules imported after an edit. Results are keyed by the finished
    geometry object, which the families store unchanged in their Glyph records. A composite
    also carries the fill of the finished base it was composed from. With a FinishedCache,
    unchanged inputs are read back with their recorded fill instead of being finished again.
    """

    def __init__(self, bj, cache=None, persist=False):
        from shapely import from_wkb
        geom, marks, charset = bj.geom, bj.marks, bj.charset
        self.finished = {}
        real_fill, real_finish, real_compose = geom.fill_pinches, geom.finish, marks.compose
        added, composed = [], {}

        def fill_pinches(g, *args, **kwargs):
            out = real_fill(g, *args, **kwargs)
            added.append(out.area - geom._clean(g).area)
            return out

        def compose(ch, base, names, fin, *args, **kwargs):
            out = real_compose(ch, base, names, fin, *args, **kwargs)
            # compose draws marks above on dotless ı and ȷ, so the decomposed base letter is not
            # always the glyph it read.
            composed[id(out)] = (out, fin[marks.mark_base(base, names)])
            return out

        def finish(g):
            key = FinishedCache.key(g) if cache else None
            hit = cache.get(key) if cache else None
            if hit:
                area, wkb = hit
                out = from_wkb(wkb)
            else:
                added.clear()
                out = real_finish(g)
                area = sum(added)
                if cache:
                    cache.put(key, area, out.wkb, persist)
            _, base = composed.pop(id(g), (None, None))
            self.finished[id(out)] = (out, area, base)
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


def fill_change(before_meter, before, after_meter, after, limit):
    """(before, after, warn) filled areas for one glyph; warn when an edit adds more than limit w².

    Finishing fills negative space narrower than about 2w with ink. Acute joins (v, k, N) are
    filled by design, so only fill an edit adds beyond the original glyph is reported.
    Unmetered glyphs never warn.
    """
    a, b = before_meter.filled(before), after_meter.filled(after)
    if a is None or b is None:
        return None, None, False
    return round(a, 2), round(b, 2), b - a > limit


def checks(g, bj, title):
    """The geometry checks of one finished glyph; TunerError when its outline cannot be checked."""
    if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon", "MultiPolygon"):
        raise TunerError(f"{title}: the edit leaves no valid outline (the ink is empty or crosses itself).",
                         "invalid_glyph")
    extent = max(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1])
    if extent > MAX_EXTENT:
        raise TunerError(f"{title}: the edit makes the glyph {extent:.0f}w across, far beyond any real glyph.",
                         "invalid_glyph")
    r = bj.verify.check_glyph(g)
    ps = bj.glyphs.pieces(g)
    gap = min((a.distance(b) for i, a in enumerate(ps) for b in ps[i + 1:]), default=None)
    r["piece_gap"] = round(gap, 3) if gap is not None else None
    r["ok"] = r["ok"] and (gap is None or gap >= bj.line_min)
    return r


def check_message(title, report, bj):
    problems = []
    if report["thin"]:
        problems.append("ink narrower than 2w, which cannot print")
    if report["islands"]:
        problems.append("a hole narrower than 2w enclosed by ink")
    gap = report["piece_gap"]
    if gap is not None and gap < bj.line_min:
        problems.append(f"separate pieces only {gap:g}w apart (at least {bj.line_min:g}w)")
    return f"{title} fails the print checks: {'; '.join(problems) or 'see the readouts'}."


def tab_too_wide(bj, family, char, glyph):
    if family == "T" and char.isascii() and char.isdigit() and glyph.width > bj.tab_digit:
        return (f"Tab {char} is {glyph.width:.2f}w wide. Tab gives every digit the same {bj.tab_cell:g}w cell, so a "
                f"digit wider than {bj.tab_digit:g}w comes closer than {bj.line_min:g}w to its neighbours.")
    return None


def absent(bj, family, chars):
    """Why the unedited family has no glyph for chars (only Mono leaves characters out)."""
    listed = ", ".join(chars)
    if family == "M":
        return f"Mono has no {listed}: wider than Mono's {bj.mono_max:g}w limit."
    return f"{FAMILY_NAMES[family]} has no {listed}."


def disappeared(bj, family, char):
    if family == "M":
        return (f"Mono leaves out {char}: after this edit its ink is wider than Mono's {bj.mono_max:g}w limit. "
                "Narrow the glyph, or undo the last change.")
    return f"{FAMILY_NAMES[family]} no longer has a glyph for {char} after this edit."


OVERRUN = re.compile(r"fillets overrun segment (\(.+?\)) -> (\(.+?\)): ([\d.]+) \+ ([\d.]+) > ([\d.]+)")


def _point(text):
    return "(" + ", ".join(f"{float(v):g}" for v in text.strip("()").split(",")) + ")"


def failing_target(exc, catalog):
    """The innermost catalogued construction on the traceback of an exception, or None.

    Edited modules are compiled under their repository path and unedited ones keep their
    absolute file name, so both map back to a source path and line.
    """
    for frame in reversed(traceback.extract_tb(exc.__traceback__)):
        path = frame.filename.replace("\\", "/")
        if path not in SOURCE_PATHS:
            try:
                path = Path(frame.filename).resolve().relative_to(ROOT).as_posix()
            except (OSError, ValueError):
                continue
        target = catalog.target_at(path, frame.lineno) if path in SOURCE_PATHS else None
        if target:
            return target
    return None


def explain(exc, catalog):
    """A plain-language reason why the edited sources could not be built."""
    target = failing_target(exc, catalog)
    where = catalog.title(target) if target else "The edited glyph sources"
    match = OVERRUN.fullmatch(str(exc)) if isinstance(exc, ValueError) else None
    if match:
        need = float(match[3]) + float(match[4])
        return (f"{where}: the rounded corners at {_point(match[1])} and {_point(match[2])} together need {need:g}w "
                f"of a segment only {float(match[5]):g}w long. Reduce the corner radius or lengthen the segment.")
    if isinstance(exc, ValueError) and str(exc).startswith("solve:"):
        return (f"{where}: no position of its automatically placed point puts the ink on the guide line with "
                "these values. Try values closer to the original.")
    if isinstance(exc, ArithmeticError):
        return (f"{where} cannot be drawn with these values: two neighbouring points coincide, or a corner's "
                "points lie on one line. Move the point, or undo the last change.")
    return f"{where} cannot be built with these values. Undo the last change, or try a value closer to the original."


class Failures(list):
    """Failure objects for the page: one per family, glyph (None for the preview line) and kind of problem."""

    def add(self, family, char, code, message):
        if not any(f["family"] == family and f["char"] == char and f["code"] == code for f in self):
            self.append({"family": family, "char": char, "code": code, "message": message})

    def of(self, family, char):
        return any(f["family"] == family and f["char"] == char for f in self)


def options(request, bj):
    """(family, char, text, validate) from a request; TunerError for anything the UI cannot send."""
    family = request.get("family", "P")
    char = request.get("char", "a")
    text = request.get("text", "Hamburgefonts 0123")
    if family not in FAMILY_NAMES:
        raise TunerError("Choose Proportional, Tab or Mono.", "bad_request")
    if not isinstance(char, str) or len(char) != 1:
        raise TunerError("Choose one character to preview.", "bad_request")
    if not isinstance(text, str) or len(text) > MAX_TEXT or any(ord(c) < 32 for c in text):
        raise TunerError(f"The preview text must be one line of at most {MAX_TEXT} characters.", "bad_request")
    if char not in bj.charset.CHARS:
        raise TunerError(f"Fillaprint has no glyph for {char} (U+{ord(char):04X}).", "no_glyph")
    text = "".join(bj.charset.ALIASES.get(c, c) for c in text)
    unknown = sorted({c for c in text if c != " " and c not in bj.charset.CHARS})
    if unknown:
        listed = ", ".join(f"{c} (U+{ord(c):04X})" for c in unknown)
        raise TunerError(f"Fillaprint has no glyph for {listed}. Remove it from the preview text.", "text_glyphs")
    return family, char, text, request.get("validate", False) is True


def run(request):
    if not isinstance(request, dict):
        raise TunerError("Expected a JSON object.", "bad_request")
    catalog = Catalog(families=False)
    edited = catalog.edited_sources(request.get("session"))
    bj = Beadjoint()
    family, char, text, validate = options(request, bj)
    # The selected family first, so an edit that breaks it fails before the others are built.
    names = [family] + [f for f in FAMILY_NAMES if validate and f != family]

    cache = FinishedCache(os.environ.get(CACHE_ENV))
    before_meter = FillMeter(bj, cache, persist=True)
    baseline = {f: bj.families[f]() for f in names}
    try:
        cache.save()
    except OSError:
        pass    # the cache only saves time
    if char not in baseline[family]:
        raise TunerError(absent(bj, family, [char]) + " Preview it in Proportional or Tab.", "not_in_family")
    missing = sorted({c for c in text if c != " " and c not in baseline[family]})
    if missing:
        raise TunerError(absent(bj, family, missing) + " Remove it from the preview text, or preview Proportional "
                         "or Tab.", "text_glyphs")
    before = baseline[family][char].geom

    if edited:
        try:
            bj = Beadjoint.reload(edited)
        except Exception as exc:    # module-level constructions (marks.SHAPES) are built on import
            raise TunerError(explain(exc, catalog), "construction") from exc
        after_meter = FillMeter(bj, cache)
    else:
        after_meter = before_meter
    failures, after = Failures(), {}
    for f in names:
        try:
            after[f] = bj.families[f]()
        except Exception as exc:
            if f == family:
                raise TunerError(explain(exc, catalog), "construction") from exc
            target = failing_target(exc, catalog)
            failures.add(f, target["char"] if target else None, "error", explain(exc, catalog))

    glyphs = after[family]
    if char not in glyphs:
        raise TunerError(disappeared(bj, family, char), "disappeared")
    title = f"{FAMILY_NAMES[family]} {char}"
    current = glyphs[char].geom
    result = {"before": outline(before), "after": outline(current), "bounds": list(before.union(current).bounds),
              "checks": checks(current, bj, title), "width": round(glyphs[char].width, 4), "family": family,
              "changed": [], "failures": failures, "warnings": [], "validation": validate}
    if not result["checks"]["ok"]:
        failures.add(family, char, "checks", check_message(title, result["checks"], bj))
    too_wide = tab_too_wide(bj, family, char, glyphs[char])
    if too_wide:
        failures.add(family, char, "tabular_width", too_wide)
    fill_before, fill_after, fill_warn = fill_change(before_meter, before, after_meter, current, bj.fill_warn)
    result["fill"] = {"before": fill_before, "after": fill_after, "warn": fill_warn}
    set_text(result, bj, family, text, glyphs, failures)
    if validate:
        for f in FAMILY_NAMES:
            if f in after:
                validate_family(result, bj, f, baseline, after[f], before_meter, after_meter, failures)
    result["failures"] = list(failures)
    return result


def set_text(result, bj, family, text, glyphs, failures):
    """The preview line. A glyph the edit removed is left out of it and reported."""
    for c in sorted({c for c in text if c != " " and c not in glyphs}):
        failures.add(family, c, "disappeared", disappeared(bj, family, c))
    line = bj.setters[family]("".join(c for c in text if c == " " or c in glyphs), glyphs)
    result["text_paths"] = [outline(g) for _, g, _ in line]
    result["text_bounds"] = [min(g.bounds[0] for _, g, _ in line), min(g.bounds[1] for _, g, _ in line),
                             max(g.bounds[2] for _, g, _ in line), max(g.bounds[3] for _, g, _ in line)] if line else [0, -4, 10, 10]
    gaps = bj.verify.line_gaps([(c, g) for c, g, _ in line])
    closest = min(gaps, key=lambda g: g[2], default=None)
    result["text_gap"] = round(closest[2], 3) if closest else None
    if closest and closest[2] < bj.line_min:
        a, b, d = closest
        failures.add(family, None, "text_gap", f"In the preview text, {a} and {b} are only {d:.2f}w apart; glyphs "
                                               f"must stay at least {bj.line_min:g}w apart.")


def validate_family(result, bj, family, baseline, new, before_meter, after_meter, failures):
    """Check every glyph of one family that the edit changed; a failing glyph does not stop the rest."""
    old = baseline[family]
    for c in sorted(old.keys() - new.keys()):
        failures.add(family, c, "disappeared", disappeared(bj, family, c))
        result["changed"].append({"family": family, "char": c, "checks": None, "fill_warn": False, "failed": True,
                                  "disappeared": True})
    for c, glyph in new.items():
        if c in old and glyph.geom.equals_exact(old[c].geom, 1e-8):
            continue
        title = f"{FAMILY_NAMES[family]} {c}"
        entry = {"family": family, "char": c, "checks": None, "fill_warn": False}
        try:
            entry["checks"] = checks(glyph.geom, bj, title)
            # A glyph that newly fits Mono has no Mono original; every character is in P.
            reference = old.get(c) or baseline["P"].get(c)
            *_, entry["fill_warn"] = fill_change(before_meter, reference.geom if reference else None, after_meter,
                                                 glyph.geom, bj.fill_warn)
        except TunerError as exc:
            failures.add(family, c, "checks", str(exc))
        except Exception:
            traceback.print_exc()
            failures.add(family, c, "error", f"{title} could not be checked with these values. Undo the last change, "
                                             "or try a value closer to the original.")
        else:
            if not entry["checks"]["ok"]:
                failures.add(family, c, "checks", check_message(title, entry["checks"], bj))
            too_wide = tab_too_wide(bj, family, c, glyph)
            if too_wide:
                failures.add(family, c, "tabular_width", too_wide)
        entry["failed"] = failures.of(family, c)
        if entry["fill_warn"]:
            result["warnings"].append(f"{family}:{c}")
        result["changed"].append(entry)


def main():
    try:
        output, status = json.dumps(run(json.load(sys.stdin)), allow_nan=False), 0
    except TunerError as exc:
        output, status = json.dumps(exc.payload()), 1
    except Exception:
        traceback.print_exc()       # for the terminal running the tuner; the browser gets a plain message
        output = json.dumps({"error": "The preview failed unexpectedly. Undo the last change, or restart the tuner.",
                             "code": "error"})
        status = 1
    print(output)
    sys.exit(status)


if __name__ == "__main__":
    main()
