"""Disposable geometry worker; a bad coordinate cannot poison later previews.

Reads one preview request as JSON on standard input and prints the result, or
{"error": message, "code": short code} with exit status 1, as JSON.
"""
import hashlib
import hmac
import importlib
import importlib.abc
import importlib.util
import inspect
import json
import math
import os
import re
import struct
import sys
import traceback
import types
import unicodedata
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
        self.marks, self.verify = load("marks"), load("verify")
        self.families = {"P": self.charset.full_p, "T": self.charset.full_mixed, "M": self.charset.full_m}
        self.setters = {"P": self.setting.kerned, "T": self.setting.mixed, "M": self.setting.tabular}
        self.line_min = self.verify.LINE_MIN          # least distance between separate pieces of ink
        self.fill_warn = self.geom.PINCH_MIN_AREA     # w²: the size of one pinch that finishing fills
        self.mono_max = self.charset.MONO_MAX         # widest ink Mono keeps
        self.tab_cell = self.setting.CELL_F            # Tab centres every digit in a cell this wide
        self.tab_digit = self.setting.FIGURE_MAX       # widest digit ink that keeps the line gap between cells
        self.max_thickness = self.verify.SHIPPED_MAX_T  # thickest ink the build accepts in a finished glyph

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


# Set by the server: a private directory that lives as long as it does, and a random secret for
# this run that authenticates the cache records. The secret stays in memory and the environment.
CACHE_ENV = "FILLAPRINT_TUNER_CACHE"
CACHE_SECRET_ENV = "FILLAPRINT_TUNER_CACHE_SECRET"
_RECORD = struct.Struct("<32sdI")   # cache key, pinch-fill area, output size; then the output and its HMAC
_MAC_SIZE = hashlib.sha256().digest_size
# Larger files are neither written nor read. All three unedited families take about 14 MB.
MAX_CACHE_BYTES = 64 * 1024 * 1024
# The functions and settings that turn raw geometry into a finished glyph. Their code and values
# are part of every cache key, so a glyph finished by different code is never read back.
FINISHING = ("finish", "soft", "fill_pinches", "fillet_inside", "_clean", "_robust")
FINISHING_SETTINGS = ("QS", "PINCH_R", "PINCH_MIN_AREA", "FILLET_MIN_AREA")


def _hash_code(h, code):
    h.update(code.co_code)
    h.update(repr(code.co_names).encode())
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            _hash_code(h, const)
        elif isinstance(const, frozenset):      # set order follows string hashing, which varies per process
            h.update(repr(sorted(map(repr, const))).encode())
        else:
            h.update(repr(const).encode())


def finishing_fingerprint(geom):
    """A digest of the finishing code and settings in geom, the Python bytecode version and GEOS.

    Bytecode rather than source text: edited modules are compiled from memory, and an edit
    elsewhere in geom.py (the dot radius) leaves finishing, and so the cache, unchanged.
    """
    import shapely
    h = hashlib.sha256()
    for name in FINISHING:
        fn = inspect.unwrap(getattr(geom, name))
        _hash_code(h, fn.__code__)
        h.update(repr((fn.__defaults__, fn.__kwdefaults__)).encode())
    settings = tuple(getattr(geom, name) for name in FINISHING_SETTINGS)
    h.update(repr((settings, shapely.__version__, shapely.geos_version_string, sys.version_info[:2])).encode())
    return h.digest()


def cache_secret():
    """The server's per-run cache secret from the environment, or None (then nothing is persisted)."""
    try:
        secret = bytes.fromhex(os.environ.get(CACHE_SECRET_ENV, ""))
    except ValueError:
        return None
    return secret if len(secret) >= 16 else None


class FinishedCache:
    """Finished glyphs from earlier workers, keyed by the finishing code and the exact input geometry.

    Finishing is a pure function of its input and dominates preview time, so a glyph whose
    input is unchanged is read back instead of finished again. Only glyphs finished from the
    unedited sources are written to disk; edited results stay in this process.

    The file lives in the server's private temporary directory. Every record carries an HMAC
    under a secret the server generates for each run and passes to its workers in their
    environment; it is never written to disk, and a record that fails verification is ignored.
    That makes the file tamper-evident against processes that can write it but cannot read the
    server's memory or environment; it is not a boundary against processes that can. WKB
    parsing cannot execute code, and a record that does not parse is treated as a miss.
    """

    def __init__(self, directory=None, secret=None):
        self.secret = secret
        self.path = os.path.join(directory, "finished-v2.bin") if directory and secret else None
        self.entries, self.unsaved, self.volatile = {}, False, set()
        if self.path:
            self._load()

    def _mac(self, body):
        return hmac.new(self.secret, body, hashlib.sha256).digest()

    def _load(self):
        try:
            if os.path.getsize(self.path) > MAX_CACHE_BYTES:
                return
            with open(self.path, "rb") as f:
                data = f.read(MAX_CACHE_BYTES + 1)
        except OSError:
            return
        offset = 0
        while offset + _RECORD.size <= len(data):
            key, area, size = _RECORD.unpack_from(data, offset)
            end = offset + _RECORD.size + size + _MAC_SIZE
            if end > len(data):
                break       # truncated: the rest cannot be framed
            body = data[offset:end - _MAC_SIZE]
            if hmac.compare_digest(self._mac(body), data[end - _MAC_SIZE:end]) and math.isfinite(area):
                self.entries[key] = (area, body[_RECORD.size:])
            offset = end

    @staticmethod
    def key(fingerprint, geom):
        return hashlib.sha256(fingerprint + geom.wkb).digest()

    def get(self, key):
        """(fill area, finished geometry) for key, or None; a record that does not parse is dropped."""
        from shapely import from_wkb
        from shapely.errors import ShapelyError
        entry = self.entries.get(key)
        if entry is None:
            return None
        try:
            return entry[0], from_wkb(entry[1])
        except (ShapelyError, ValueError, TypeError):
            self.entries.pop(key, None)
            self.volatile.discard(key)
            return None

    def put(self, key, area, wkb, persist):
        self.entries[key] = (area, wkb)
        if persist:
            self.unsaved = True
            self.volatile.discard(key)
        else:
            self.volatile.add(key)

    def save(self):
        if not (self.path and self.unsaved):
            return
        records = []
        for k, (a, w) in self.entries.items():
            if k not in self.volatile:
                body = _RECORD.pack(k, a, len(w)) + w
                records.append(body + self._mac(body))
        data = b"".join(records)
        self.unsaved = False
        if len(data) > MAX_CACHE_BYTES:
            # _load would ignore such a file and every later worker would start cold; keep the
            # previous file and this worker's entries in memory instead, and say so.
            print(f"tuner worker: glyph cache of {len(data) / 2 ** 20:.0f} MB exceeds "
                  f"{MAX_CACHE_BYTES / 2 ** 20:.0f} MB and was not saved", file=sys.stderr)
            return
        partial = self.path + ".partial"
        with open(partial, "wb") as f:
            f.write(data)
        os.replace(partial, self.path)


class FillMeter:
    """Record how much ink fill_pinches adds each time charset finishes a glyph.

    charset binds finish and calls marks.compose by name, and geom.finish calls fill_pinches
    through its module globals, so the wrappers go on the modules of one Beadjoint: create a
    new meter for the modules imported after an edit. Results are keyed by the finished
    geometry object, which the families store unchanged in their Glyph records. A composite
    also carries the fill of the finished base it was composed from. Every record keeps the
    geometry finishing received, which the fused-pieces check compares with the result. With a
    FinishedCache, unchanged inputs are read back with their recorded fill instead of being
    finished again; the recorded input is the one this build passed either way.
    """

    def __init__(self, bj, cache=None, persist=False):
        geom, marks, charset = bj.geom, bj.marks, bj.charset
        self.fingerprint = finishing_fingerprint(geom)
        self.finished = {}
        self.outputs = {}       # cache key of an input -> its finished glyph, to explain left-out glyphs
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
            key = FinishedCache.key(self.fingerprint, g)
            hit = cache.get(key) if cache else None
            if hit:
                area, out = hit
            else:
                added.clear()
                out = real_finish(g)
                area = sum(added)
                if cache:
                    cache.put(key, area, out.wkb, persist)
            _, base = composed.pop(id(g), (None, None))
            self.finished[id(out)] = (out, area, base, g)
            self.outputs[key] = out
            return out

        for wrapper, real in ((fill_pinches, real_fill), (compose, real_compose), (finish, real_finish)):
            wrapper.__wrapped__ = real
        geom.fill_pinches, marks.compose, charset.finish = fill_pinches, compose, finish

    def finished_from(self, raw):
        """The finished glyph this meter recorded for raw input geometry, or None."""
        return self.outputs.get(FinishedCache.key(self.fingerprint, raw))

    def finish_input(self, geom):
        """The geometry finishing received for a finished glyph, or None if unmetered."""
        record = self.finished.get(id(geom))
        return record[3] if record else None

    def filled(self, geom, depth=0):
        """Filled area in w² for a finished glyph, including its base's fill; None if unmetered."""
        record = self.finished.get(id(geom))
        if record is None or depth > 4:
            return None
        _, area, base, _ = record
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


def usable(g):
    """Whether the checks and the setting can measure g: nonempty, valid, polygonal, finite."""
    return (not g.is_empty and g.is_valid and g.geom_type in ("Polygon", "MultiPolygon")
            and all(math.isfinite(v) for v in g.bounds))


def no_outline(title, g):
    if g.is_empty or not all(math.isfinite(v) for v in g.bounds):
        return f"{title}: the edit leaves no ink to print."
    return f"{title}: the edit leaves an outline that is not a valid shape (it crosses itself)."


def glyph_title(family, char):
    return f"{char} ({FAMILY_NAMES[family]})"


def joined_by_finishing(bj, meter, family, char, glyph):
    """Whether finishing joined pieces of the glyph that its input kept apart, as the build checks:
    verify.fused_pieces on what finishing received and returned, less the family's designed joins."""
    source = meter.finish_input(glyph.geom)
    if source is None or char in bj.verify.FUSED_BY_DESIGN.get(family, ()):
        return False
    return bool(bj.verify.fused_pieces({char: glyph}, {char: source}))


def checks(g, bj, title, fused=False):
    """The geometry checks of one finished glyph, with the gates the build fails on: no thin ink or
    thin holes, pieces LINE_MIN apart, no ink over SHIPPED_MAX_T and no pieces joined by finishing
    (fused, from joined_by_finishing). TunerError when the outline cannot be checked."""
    if not usable(g):
        raise TunerError(no_outline(title, g), "invalid_glyph")
    extent = max(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1])
    if extent > MAX_EXTENT:
        raise TunerError(f"{title}: the edit makes the glyph {extent:.0f}w across, far beyond any real glyph.",
                         "invalid_glyph")
    r = bj.verify.check_glyph(g)
    gap = bj.verify.piece_gap(g)                     # inf for a glyph of one piece
    r["piece_gap"] = round(gap, 3) if math.isfinite(gap) else None
    r["fused"] = fused
    r["ok"] = r["ok"] and gap >= bj.line_min and r["thickness"] <= bj.max_thickness and not fused
    return r


def check_message(title, report, bj):
    problems = []
    if report["fused"]:
        problems.append(f"finishing joined separate pieces — keep them at least {bj.line_min:g}w apart")
    if report["thickness"] > bj.max_thickness:
        problems.append(f"it is {report['thickness']:g}w thick at its thickest; the fonts allow at most "
                        f"{bj.max_thickness:g}w")
    if report["thin"]:
        problems.append("it has ink narrower than 2w, which cannot print")
    if report["islands"]:
        problems.append("it encloses a hole narrower than 2w")
    gap = report["piece_gap"]
    if gap is not None and gap < bj.line_min:
        problems.append(f"separate pieces are only {gap:g}w apart (at least {bj.line_min:g}w)")
    return f"{title}: {'; '.join(problems) or 'it fails the print checks'}."


def tab_too_wide(bj, family, char, glyph):
    if family == "T" and char.isascii() and char.isdigit() and glyph.width > bj.tab_digit:
        return (f"{glyph_title('T', char)} is {glyph.width:.2f}w wide. Tab gives every digit the same "
                f"{bj.tab_cell:g}w cell, so a digit wider than {bj.tab_digit:g}w comes closer than "
                f"{bj.line_min:g}w to its neighbours.")
    return None


def shown(c):
    """A character as a message shows it: invisible and control characters by code point only."""
    code = f"U+{ord(c):04X}"
    return code if unicodedata.category(c)[0] in "CZ" else f"{c} ({code})"


def absent(bj, family, chars):
    """Why the unedited family has no glyph for chars (only Mono leaves characters out)."""
    listed = ", ".join(chars)
    if family == "M":
        return f"Mono doesn't include {listed}: wider than Mono's {bj.mono_max:g}w limit."
    return f"{FAMILY_NAMES[family]} doesn't include {listed}."


def left_out(bj, meter, family, char, depth=0):
    """Why the edited family has no glyph for char. Only Mono leaves glyphs out, for ink wider
    than its cell; an outline the edit emptied measures NaN wide and is left out as well, which
    must not read as "too wide"."""
    if family != "M":
        return f"{FAMILY_NAMES[family]} no longer has a glyph for {char} after this edit."
    raw = bj.charset.raw_m().get(char)
    parts = bj.marks.decompose(char) if raw is None else None
    if parts and depth < 3:
        base = bj.marks.mark_base(*parts)
        g = meter.finished_from(bj.charset.raw_m()[base]) if base in bj.charset.raw_m() else None
        if g is not None and not usable(g):
            return f"Mono leaves out {char}: after this edit its base {base} has no ink to print."
    g = meter.finished_from(raw) if raw is not None else None
    if g is not None and not usable(g):
        return f"Mono leaves out {char}: after this edit it has no ink to print."
    width = f" ({g.bounds[2] - g.bounds[0]:.2f}w)" if g is not None else ""
    return (f"Mono leaves out {char}: after this edit its ink is wider{width} than Mono's {bj.mono_max:g}w limit. "
            "Narrow the glyph, or undo the last change.")


OVERRUN = re.compile(r"fillets overrun segment (\(.+?\)) -> (\(.+?\)): ([\d.]+) \+ ([\d.]+) > ([\d.]+)")
COINCIDENT = re.compile(r"stroke point (\(.+?\)) coincides with its neighbour.*")


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
    match = COINCIDENT.fullmatch(str(exc)) if isinstance(exc, ValueError) else None
    if match:
        return (f"{where}: the point at {_point(match[1])} sits on the point next to it, so the stroke has no "
                "direction there. Move one of them.")
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


def control(c):
    """Control characters and lone surrogates: never glyphs, and unsafe to echo into a message."""
    return unicodedata.category(c) in ("Cc", "Cs")


def options(request, bj):
    """(family, char, text, validate) from a request; TunerError for anything the UI cannot send."""
    family = request.get("family", "P")
    char = request.get("char", "a")
    text = request.get("text", "Hamburgefonts 0123")
    if family not in FAMILY_NAMES:
        raise TunerError("Choose Proportional, Tab or Mono.", "bad_request")
    if not isinstance(char, str) or len(char) != 1 or control(char):
        raise TunerError("Choose one character to preview.", "bad_request")
    if not isinstance(text, str) or len(text) > MAX_TEXT or any(control(c) for c in text):
        raise TunerError(f"The preview text must be one line of at most {MAX_TEXT} characters.", "bad_request")
    if char not in bj.charset.CHARS:
        raise TunerError(f"Fillaprint has no glyph for {shown(char)}.", "no_glyph")
    text = "".join(bj.charset.ALIASES.get(c, c) for c in text)
    unknown = sorted({c for c in text if c != " " and c not in bj.charset.CHARS})
    if unknown:
        listed = ", ".join(shown(c) for c in unknown)
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

    cache = FinishedCache(os.environ.get(CACHE_ENV), cache_secret())
    before_meter = FillMeter(bj, cache, persist=True)
    baseline = {f: bj.families[f]() for f in names}
    try:
        cache.save()
    except OSError:
        pass    # the cache only saves time
    # Mono leaves wide glyphs out, and an edit can make one fit: None then, with no original to show.
    before = baseline[family][char].geom if char in baseline[family] else None

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
        if before is None and edited:
            raise TunerError(f"{FAMILY_NAMES[family]} doesn't include {char} before this edit (wider than Mono's "
                             f"{bj.mono_max:g}w limit), and it still doesn't fit after it. Preview it in Proportional "
                             "or Tab.", "not_in_family")
        if before is None:
            raise TunerError(absent(bj, family, [char]) + " Preview it in Proportional or Tab.", "not_in_family")
        raise TunerError(left_out(bj, after_meter, family, char), "disappeared")
    missing = sorted({c for c in text if c != " " and c not in baseline[family] and c not in glyphs})
    if missing:
        raise TunerError(absent(bj, family, missing) + " Remove it from the preview text, or preview Proportional "
                         "or Tab.", "text_glyphs")
    title = glyph_title(family, char)
    current = glyphs[char].geom
    bounds = (before.union(current) if before is not None else current).bounds
    fused = joined_by_finishing(bj, after_meter, family, char, glyphs[char])
    result = {"before": outline(before) if before is not None else "", "after": outline(current), "bounds": list(bounds),
              "checks": checks(current, bj, title, fused), "width": round(glyphs[char].width, 4), "family": family,
              "changed": [], "failures": failures, "warnings": [], "validation": validate}
    if not result["checks"]["ok"]:
        failures.add(family, char, "checks", check_message(title, result["checks"], bj))
    too_wide = tab_too_wide(bj, family, char, glyphs[char])
    if too_wide:
        failures.add(family, char, "tabular_width", too_wide)
    fill_before, fill_after, fill_warn = fill_change(before_meter, before, after_meter, current, bj.fill_warn)
    # Fill that joins pieces is a failure; the amber warning is for fill that does not.
    result["fill"] = {"before": fill_before, "after": fill_after, "warn": fill_warn and not fused}
    set_text(result, bj, after_meter, family, text, glyphs, failures)
    if validate:
        for f in FAMILY_NAMES:
            if f in after:
                validate_family(result, bj, f, baseline, after[f], before_meter, after_meter, failures)
    result["failures"] = list(failures)
    return result


def set_text(result, bj, meter, family, text, glyphs, failures):
    """The preview line. A glyph the edit removed or emptied is left out of it and reported."""
    for c in sorted({c for c in text if c != " "}):
        if c not in glyphs:
            failures.add(family, c, "disappeared", left_out(bj, meter, family, c))
        elif not usable(glyphs[c].geom):
            failures.add(family, c, "checks", no_outline(glyph_title(family, c), glyphs[c].geom))
    kept = "".join(c for c in text if c == " " or c in glyphs and usable(glyphs[c].geom))
    line = bj.setters[family](kept, glyphs)
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
        failures.add(family, c, "disappeared", left_out(bj, after_meter, family, c))
        result["changed"].append({"family": family, "char": c, "checks": None, "fill_warn": False, "failed": True,
                                  "disappeared": True})
    for c, glyph in new.items():
        if c in old and glyph.geom.equals_exact(old[c].geom, 1e-8):
            continue
        title = glyph_title(family, c)
        entry = {"family": family, "char": c, "checks": None, "fill_warn": False}
        try:
            fused = joined_by_finishing(bj, after_meter, family, c, glyph)
            entry["checks"] = checks(glyph.geom, bj, title, fused)
            # A glyph that newly fits Mono has no Mono original; every character is in P.
            reference = old.get(c) or baseline["P"].get(c)
            *_, fill_warn = fill_change(before_meter, reference.geom if reference else None, after_meter,
                                        glyph.geom, bj.fill_warn)
            entry["fill_warn"] = fill_warn and not fused
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


def finite(value, path="result"):
    """value with every non-finite number replaced by None. JSON has no NaN, and one unmeasurable
    number must not cost the whole preview; the terminal running the tuner is told where it was."""
    if isinstance(value, float) and not math.isfinite(value):
        print(f"tuner worker: non-finite number at {path} replaced by null", file=sys.stderr)
        return None
    if isinstance(value, dict):
        return {k: finite(v, f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(v, f"{path}[{i}]") for i, v in enumerate(value)]
    return value


def main():
    try:
        output, status = json.dumps(finite(run(json.load(sys.stdin))), allow_nan=False), 0
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
