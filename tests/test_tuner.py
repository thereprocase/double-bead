"""Contribution safety and actual source → edited geometry → Git patch round trips."""
import ast
import copy
import errno
import functools
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from beadjoint import charset, geom, glyphs, latin, verify
from tuner import serve
from tuner.model import ACCENTS, FUNCTIONS, ROOT, SHARED, SOURCE_PATHS, Catalog, TunerError, number, source_commit
from tuner.serve import MAX_BODY, Handler, TunerServer
from tuner.worker import CACHE_ENV, Beadjoint, absent, explain, fill_change

HEX = "0123456789abcdef0123456789abcdef01234567"


@functools.cache
def catalog():
    """The full catalog, built once: tests only read it."""
    return Catalog()


def copy_sources(root):
    for name, source in catalog().sources.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(source)


def target(char, group):
    return next(t for t in catalog().targets if t["char"] == char and t["group"] == group)


def slot(char, group, label):
    return next(s for s in target(char, group)["slots"] if s["label"] == label)


def new_session():
    return {"schema": 1, "sources": dict(catalog().hashes), "values": {}}


def run_worker(request, env=None, timeout=300):
    process = subprocess.run([sys.executable, "-m", "tuner.worker"], input=json.dumps(request), text=True,
                             capture_output=True, cwd=ROOT, timeout=timeout, env=env)
    return process, json.loads(process.stdout)


class SourceEditing(unittest.TestCase):
    def setUp(self):
        self.catalog = catalog()
        self.session = new_session()

    def test_noop_produces_no_patch(self):
        self.assertEqual(self.catalog.patch(self.session), "")

    def test_signed_numeric_edit_preserves_the_rest_of_the_source(self):
        s = next(s for s in target("b", "Base")["slots"] if s["value"] == -4)
        self.session["values"][s["id"]] = -3.75
        edited = self.catalog.edited_sources(self.session)[s["path"]]
        original = self.catalog.sources[s["path"]]
        self.assertEqual(edited, original[:s["start"]] + b"-3.75" + original[s["end"]:])

    def test_literals_are_plain_and_round_trip(self):
        s = slot("b", "Base", "S2 point 2 x")
        original = self.catalog.sources[s["path"]]
        for value, literal in ((7.0, b"7"), (1e-07, b"1e-07"), (-2.25, b"-2.25")):
            self.session["values"] = {s["id"]: value}
            edited = self.catalog.edited_sources(self.session)[s["path"]]
            self.assertEqual(edited, original[:s["start"]] + literal + original[s["end"]:])
            _, line, col = s["id"].rsplit(":", 2)
            nodes = [n for n in ast.walk(ast.parse(edited)) if getattr(n, "lineno", None) == int(line)
                     and getattr(n, "col_offset", None) == int(col) and number(n) is not None]
            self.assertEqual(number(nodes[0]), value)

    def assert_patch_applies(self, patch):
        subprocess.run(["git", "apply", "--check", "-"], input=patch, text=True, cwd=ROOT, check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root)
            subprocess.run(["git", "apply", "-"], input=patch, text=True, cwd=root, check=True, capture_output=True)
            for name, expected in self.catalog.edited_sources(self.session).items():
                self.assertEqual((root / name).read_bytes(), expected)

    def test_unicode_column_offsets_and_patch_apply(self):
        s = target("Ω", "Mono")["slots"][0]
        self.session["values"][s["id"]] = s["value"] + .1
        self.assert_patch_applies(self.catalog.patch(self.session))

    def test_patch_spanning_two_files_applies(self):
        self.session["values"][slot("b", "Base", "S2 point 2 x")["id"]] = 6.5
        self.session["values"][slot("H", "Capitals", "S3 point 1 y")["id"]] = 2.5
        patch = self.catalog.patch(self.session)
        self.assertEqual(patch.count("diff --git"), 2)
        self.assert_patch_applies(patch)

    def test_rejects_code_nonfinite_out_of_range_and_unknown_slots(self):
        s = target("a", "Base")["slots"][0]
        for value in ("__import__('os')", float("nan"), float("inf"), True, 100):
            self.session["values"] = {s["id"]: value}
            with self.subTest(value=value), self.assertRaises(TunerError):
                self.catalog.edited_sources(self.session)
        self.session["values"] = {"../../other.py:1:0": 1}
        with self.assertRaises(TunerError):
            self.catalog.edited_sources(self.session)

    def test_radius_range(self):
        s = slot("z", "Base", "S1 point 2 corner radius")
        for value in (0, 8):
            self.session["values"] = {s["id"]: value}
            self.assertEqual(self.catalog.validate(self.session), {s["id"]: value})
        for value in (-0.5, 8.5):
            self.session["values"] = {s["id"]: value}
            with self.subTest(value=value), self.assertRaisesRegex(TunerError, "radii must be between 0 and 8w"):
                self.catalog.validate(self.session)

    def test_out_of_range_source_value_stays_valid(self):
        s = slot("M", "Shared M / W", "Rect2 x₁")
        self.assertEqual(s["value"], 40)
        self.session["values"] = {s["id"]: 40}
        self.assertEqual(self.catalog.validate(self.session), {})
        self.session["values"] = {s["id"]: 40.5}
        with self.assertRaises(TunerError):
            self.catalog.validate(self.session)

    def test_unknown_session_keys_are_ignored(self):
        self.session.update(commit="not a commit", note={"any": "thing"})
        self.assertEqual(self.catalog.patch(self.session), "")

    def test_stale_session_names_its_commit_and_the_resume_command(self):
        stale = copy.deepcopy(self.session)
        stale["sources"]["beadjoint/glyphs.py"] = "old"
        for commit, expected in ((HEX, "git switch --detach 0123456789ab"), (None, "does not record a commit"),
                                 ("; rm -rf ~", "does not record a commit")):
            stale["commit"] = commit
            with self.subTest(commit=commit), self.assertRaises(TunerError) as caught:
                self.catalog.patch(stale)
            self.assertEqual(caught.exception.code, "stale_session")
            self.assertIn(expected, str(caught.exception))
            self.assertNotIn("rm -rf", str(caught.exception))

    def test_changed_disk_source_names_the_session_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root)
            c = Catalog(root, families=False)
            (root / "beadjoint/glyphs.py").write_bytes(b"# changed")
            with self.assertRaises(TunerError) as caught:
                c.patch({**self.session, "commit": HEX})
        self.assertEqual(caught.exception.code, "sources_changed")
        self.assertIn("run: git switch --detach 0123456789ab, then restart the tuner", str(caught.exception))

    def test_source_commit_is_head_only_for_matching_sources(self):
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *SOURCE_PATHS], cwd=ROOT).returncode == 0
        self.assertEqual(source_commit(ROOT), head if clean else None)
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(source_commit(directory))


class CatalogStructure(unittest.TestCase):
    def test_invariants(self):
        c = catalog()
        groups = {t["group"] for t in c.targets}
        for construction in [*FUNCTIONS.values(), *SHARED.values()]:
            self.assertIn(construction.group, groups)
        for name in ACCENTS:
            self.assertIn("Accent " + name, groups)
        ids = [s["id"] for t in c.targets for s in t["slots"]]
        self.assertEqual(len(ids), len(set(ids)), "a slot belongs to two constructions")
        self.assertEqual(set(ids), set(c.slots))
        for t in c.targets:
            own = {s["id"] for s in t["slots"]}
            self.assertIn(t["family"], ("P", "M"))
            for s in t["slots"]:
                self.assertIn(s["path"], SOURCE_PATHS)
                literal = c.sources[s["path"]][s["start"]:s["end"]].decode()
                self.assertEqual(number(ast.parse(literal, mode="eval").body), s["value"], s["id"])
            for h in t["handles"]:
                self.assertLessEqual({h["x"], h["y"]}, own, t["id"])

    def test_labels_follow_reading_order(self):
        t = target("#", "Symbols")
        lines = catalog().sources[t["path"]].splitlines(True)
        line_start = sum(len(line) for line in lines[:t["line"] - 1])
        first = lines[t["line"] - 1].index(b"S((")
        self.assertEqual(slot("#", "Symbols", "S1 point 1 x")["start"], line_start + first + 3)
        self.assertEqual(slot("#", "Symbols", "S2 point 1 x")["value"], 6)

    def test_crlf_sources_are_refused_with_the_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root)
            path = root / "beadjoint/latin.py"
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            with self.assertRaises(ValueError) as caught:
                Catalog(root, families=False)
        self.assertIn("git rm -r --cached -q beadjoint && git reset --hard", str(caught.exception))

    def assert_refused(self, path, old, new, message):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root)
            source = (root / path).read_bytes()
            self.assertIn(old, source)
            (root / path).write_bytes(source.replace(old, new, 1))
            with self.assertRaises(ValueError) as caught:
                Catalog(root, families=False)
        self.assertIn(message, str(caught.exception))

    def test_renamed_constructions_stop_the_tuner(self):
        self.assert_refused("beadjoint/latin.py", b"def capitals(", b"def capital_letters(", "capitals() (Capitals)")
        self.assert_refused("beadjoint/latin.py", b"    head = ", b"    top = ", "head in symbols()")
        self.assert_refused("beadjoint/marks.py", b'"breve":', b'"brevis":', "no preview character")
        self.assert_refused("beadjoint/geom.py", b"\nDOT = ", b"\nDOT_R = ", "DOT")

    def test_construction_without_parameters_stops_the_tuner(self):
        self.assert_refused("beadjoint/latin.py", b"def square_w():", b"def square_w():\n    return None\n\n\ndef _w():",
                            "square_w()")

    def test_replaced_constructions_are_dropped(self):
        c = catalog()
        expected = {("Base", "1"), ("Base", "w"), ("Mono", "w")}
        self.assertEqual(set(c.superseded), expected)
        for group, char in expected:
            self.assertFalse([t for t in c.targets if (t["group"], t["char"]) == (group, char)])
        self.assertTrue([t for t in c.targets if (t["group"], t["char"]) == ("Footed 1", "1")])

    @staticmethod
    def raw_outputs():
        """Each construction function's output, called as charset calls it (independent of tuner/model.py)."""
        p = glyphs._raw_p()
        cap, sym = latin.capitals(), latin.symbols(p)
        out = {"_raw_p": p, "capitals": cap, "symbols": sym, "specials": latin.specials(p, cap, sym),
               "mono_narrow": latin.mono_narrow(), "_raw_m_rebuilt": glyphs._raw_m_rebuilt(),
               "_raw_one_tabular": glyphs._raw_one_tabular(), "square_w": latin.square_w(),
               "_pointed_m": latin._pointed_m(), "extras": latin.extras(), "mono_extras": latin.mono_extras()}
        return out

    def constructions(self, family):
        """(target, raw output) for every whole-glyph construction of a family."""
        out, found = self.raw_outputs(), []
        pieces = {s.group for s in SHARED.values()}
        for t in catalog().targets:
            tree = ast.parse(catalog().sources[t["path"]])
            fn = next((n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.lineno <= t["line"] <= n.end_lineno), None)
            if fn in out and t["family"] == family and t["group"] not in pieces:
                found.append((t, out[fn] if not isinstance(out[fn], dict) else out[fn][t["char"]]))
        return found

    def test_every_proportional_construction_is_what_the_fonts_use(self):
        raw = charset.raw_p()
        found = self.constructions("P")
        self.assertGreater(len(found), 140)
        for t, built in found:
            self.assertEqual(raw[t["char"]].wkb, built.wkb, f"{t['group']} {t['char']} is not what Proportional uses")

    def test_every_mono_construction_is_what_the_fonts_use(self):
        raw = charset.raw_m()
        found = self.constructions("M")
        self.assertGreater(len(found), 20)
        for t, built in found:
            # glyphs.set_m softens the rebuilt glyphs before charset assembles Mono
            self.assertIn(raw[t["char"]].wkb, (built.wkb, geom.soft(built).wkb), f"Mono {t['char']}")

    def test_moved_constructions_are_catalogued(self):
        groups = {(t["group"], t["char"]) for t in catalog().targets}
        self.assertLessEqual({("Specials", c) for c in "¸˛ŉ"} | {("Mono", c) for c in "ıȷ…"}, groups)

    def test_diagonals_are_exposed(self):
        n = target("N", "Capitals")
        self.assertEqual([s["value"] for s in n["slots"] if s["label"].startswith("diagonal3")], [1.111, -4, 7.889, 10])
        self.assertIn({"x": slot("N", "Capitals", "diagonal3 x₁")["id"], "y": slot("N", "Capitals", "diagonal3 y₁")["id"],
                       "label": "diagonal3.2"}, n["handles"])
        self.assertEqual(slot("®", "Symbols", "diagonal4 clip y₀")["value"], 3)
        fraction = target("½", "Shared fraction slash")
        self.assertEqual([s["value"] for s in fraction["slots"]], [0.9, 10, 4.9, -4])
        self.assertEqual(fraction["handles"], [], "the slash is shifted into each fraction")

    def test_composites_name_the_base_compose_reads(self):
        derived = catalog().derived
        self.assertEqual(derived["ñ"], {"base": "n", "marks": ["tilde"]})
        self.assertEqual(derived["í"]["base"], "ı")
        self.assertEqual(derived["į"]["base"], "i", "a mark below keeps the dotted i")
        self.assertNotIn("n", derived)
        self.assertLessEqual({d["base"] for d in derived.values()}, set(charset.raw_p()))


class WorkerLogic(unittest.TestCase):
    class Meter:
        def __init__(self, area):
            self.area = area

        def filled(self, geom):
            return self.area

    def test_limits_come_from_the_font_code(self):
        bj = Beadjoint()
        self.assertEqual(bj.fill_warn, geom.PINCH_MIN_AREA)
        self.assertEqual(bj.line_min, verify.LINE_MIN)
        self.assertEqual(bj.mono_max, charset.MONO_MAX)
        self.assertAlmostEqual(bj.tab_digit, 7.02)

    def test_fill_warning_threshold(self):
        limit = Beadjoint().fill_warn
        m = self.Meter
        self.assertFalse(fill_change(m(1.0), None, m(1.0 + limit), None, limit)[2])
        self.assertTrue(fill_change(m(1.0), None, m(1.0 + limit + 1e-6), None, limit)[2])
        self.assertEqual(fill_change(m(None), None, m(5.0), None, limit), (None, None, False))

    def test_absent_glyphs_are_explained_per_family(self):
        bj = Beadjoint()
        self.assertEqual(absent(bj, "M", ["©"]), "Mono has no ©: wider than Mono's 10w limit.")
        self.assertEqual(absent(bj, "P", ["x"]), "Proportional has no x.")

    def test_construction_errors_name_the_construction(self):
        session = new_session()
        session["values"][slot("n", "Base", "S1 point 2 corner radius")["id"]] = 8
        source = catalog().edited_sources(session)["beadjoint/glyphs.py"]
        namespace = {"__name__": "beadjoint.edited_for_test", "__package__": "beadjoint"}
        exec(compile(source, "beadjoint/glyphs.py", "exec"), namespace)
        try:            # not assertRaises: it drops the traceback that locates the construction
            namespace["_raw_p"]()
        except ValueError as exc:
            message = explain(exc, catalog())
        else:
            self.fail("the edited n should not build")
        self.assertEqual(message, "n (Base): the rounded corners at (1, 1) and (6, 1) together need 9w of a segment "
                                  "only 5w long. Reduce the corner radius or lengthen the segment.")

    def test_other_errors_have_plain_messages(self):
        for exc in (ZeroDivisionError("float division by zero"), RuntimeError("GEOS: TopologyException"),
                    ValueError("solve: target not bracketed")):
            message = explain(exc, catalog())
            with self.subTest(exc=exc):
                self.assertTrue(message.startswith("The edited glyph sources"))
                self.assertNotIn(type(exc).__name__, message)
                self.assertNotIn(str(exc), message)


class WorkerRuns(unittest.TestCase):
    def setUp(self):
        self.session = new_session()

    def edit(self, char, group, labels, value):
        for label in labels:
            self.session["values"][slot(char, group, label)["id"]] = value

    def test_edit_reaches_real_geometry_and_derived_accents(self):
        # Widen the right stem of n, preserving its width. This must flow into
        # accented n, Tab, and Mono's counter-widened n. Mono's rebuilt r stays put.
        self.edit("n", "Base", ("S1 point 3 x", "S1 point 4 x"), 6.5)
        request = {"session": self.session, "family": "P", "char": "n", "text": "n ñ ņ 0123", "validate": True}
        process, result = run_worker(request)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertNotEqual(result["before"], result["after"])
        self.assertAlmostEqual(result["width"], 7.5, places=2)
        self.assertEqual(result["failures"], [])
        changed = {(g["family"], g["char"]) for g in result["changed"]}
        self.assertIn(("P", "ñ"), changed)
        self.assertIn(("T", "n"), changed)
        self.assertIn(("M", "n"), changed)
        self.assertNotIn(("M", "r"), changed)
        self.assertFalse(any(g["failed"] for g in result["changed"]))
        self.assertEqual(result["warnings"], [])
        self.assertFalse(result["fill"]["warn"])

    def test_closing_a_counter_warns_and_the_glyph_cache_changes_nothing(self):
        # Right stem of n at x = 3.5 leaves a 0.5w slit; finishing fills it with ink, so the
        # glyph still passes the hard checks. The preview must say so rather than stay green.
        self.edit("n", "Base", ("S1 point 3 x", "S1 point 4 x"), 3.5)
        request = {"session": self.session, "family": "P", "char": "n", "text": "n", "validate": False}
        plain = {k: v for k, v in os.environ.items() if k != CACHE_ENV}
        process, result = run_worker(request, env=plain)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertTrue(result["checks"]["ok"])
        self.assertTrue(result["fill"]["warn"])
        self.assertEqual(result["fill"]["before"], 0)
        self.assertGreater(result["fill"]["after"], 3)
        # The first cached run stores the unedited font; the second reads it back.
        with tempfile.TemporaryDirectory() as directory:
            for _ in range(2):
                process, cached = run_worker(request, env={**plain, CACHE_ENV: directory})
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(cached, result)
            self.assertTrue(os.listdir(directory))

    def test_fill_warning_follows_the_dotless_base_of_accented_i_and_j(self):
        # Marks above sit on dotless ı and ȷ: a new fill in ȷ must reach ĵ, and moving the
        # dot of i must not be charged to í (its geometry does not change).
        self.edit("ȷ", "Specials", ("S1 point 3 y",), 10)
        self.edit("i", "Base", ("D2 point 1 y",), -2.2)
        request = {"session": self.session, "family": "P", "char": "í", "text": "í ĵ", "validate": True}
        process, result = run_worker(request)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertFalse(result["fill"]["warn"])
        self.assertIn("P:ȷ", result["warnings"])
        self.assertIn("P:ĵ", result["warnings"])
        self.assertNotIn("P:í", {g["family"] + ":" + g["char"] for g in result["changed"]})

    def test_validation_reports_every_failure(self):
        # n at 8.5w no longer fits Mono (its widened form is 10.5w), and a 8.5w 0 overflows Tab's
        # 9w digit cell. Both must be reported in one run, as objects the page can act on.
        self.edit("n", "Base", ("S1 point 3 x", "S1 point 4 x"), 7.5)
        self.edit("0", "Base", ("So1 point 2 x", "So1 point 3 x"), 7.5)
        request = {"session": self.session, "family": "P", "char": "n", "text": "n0", "validate": True}
        process, result = run_worker(request)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        for f in result["failures"]:
            self.assertEqual(set(f), {"family", "char", "code", "message"})
            self.assertNotIn("Beadjoint", f["message"])
        failures = {(f["family"], f["char"], f["code"]) for f in result["failures"]}
        self.assertLessEqual({("M", c, "disappeared") for c in "nñńņň"}, failures)
        self.assertIn(("T", "0", "tabular_width"), failures)
        changed = {(g["family"], g["char"]): g for g in result["changed"]}
        self.assertEqual(changed["M", "ñ"], {"family": "M", "char": "ñ", "checks": None, "fill_warn": False,
                                             "failed": True, "disappeared": True})
        self.assertTrue(changed["T", "0"]["failed"])
        self.assertFalse(changed["P", "0"]["failed"])

    def test_request_errors_are_plain(self):
        for request, code, text in (({"family": "X"}, "bad_request", "Proportional, Tab or Mono"),
                                    ({"char": "Ж"}, "no_glyph", "Fillaprint has no glyph for Ж"),
                                    ({"text": "Пa"}, "text_glyphs", "Fillaprint has no glyph for П")):
            process, result = run_worker({"session": self.session, **request})
            with self.subTest(code=code):
                self.assertEqual(process.returncode, 1)
                self.assertEqual(result["code"], code)
                self.assertIn(text, result["error"])
                self.assertNotIn("Beadjoint", result["error"])

    def test_fill_meter_covers_every_glyph(self):
        # Warnings rely on finished geometry reaching the Glyph records unchanged; a pipeline
        # change that breaks that would otherwise silence them without failing anything.
        script = ("from tuner.worker import Beadjoint, FillMeter\n"
                  "bj = Beadjoint()\n"
                  "meter = FillMeter(bj)\n"
                  "for glyphs in (bj.charset.full_p(), bj.charset.full_mixed(), bj.charset.full_m()):\n"
                  "    missing = [c for c, g in glyphs.items() if meter.filled(g.geom) is None]\n"
                  "    assert not missing, missing\n"
                  "    assert meter.filled(glyphs['N'].geom) > 1, 'acute joins are filled by design'\n"
                  "    for accented, base in (('í', 'ı'), ('ĵ', 'ȷ'), ('ñ', 'n')):\n"
                  "        assert meter.finished[id(glyphs[accented].geom)][2] is glyphs[base].geom, accented\n")
        process = subprocess.run([sys.executable, "-c", script], text=True, capture_output=True, cwd=ROOT, timeout=300)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


class LocalServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = TunerServer(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.url = f"http://127.0.0.1:{cls.port}"
        with urlopen(cls.url + "/api/catalog") as response:
            cls.catalog = json.load(response)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def session(self):
        return {"schema": 1, "sources": self.catalog["sources"], "values": {}}

    def request(self, method, path, body=None, headers=()):
        """(status, headers, parsed body) without urllib adding or checking anything."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            conn.request(method, path, body=body, headers=dict(headers))
            response = conn.getresponse()
            data = response.read()
            parsed = json.loads(data) if response.headers.get_content_type() == "application/json" else data
            return response.status, response.headers, parsed
        finally:
            conn.close()

    def post(self, payload, path="/api/preview"):
        headers = {"Content-Type": "application/json", "X-Tuner-Token": self.catalog["token"]}
        status, _, body = self.request("POST", path, json.dumps(payload).encode(), headers)
        return status, body

    def test_static_routes_and_headers(self):
        routes = {"/": "text/html; charset=utf-8", "/app.js": "text/javascript; charset=utf-8",
                  "/style.css": "text/css; charset=utf-8"}
        routes.update({f"/fonts/{f}.woff2": "font/woff2" for f in ("sans-400", "sans-600", "mono-400")})
        for path, mime in routes.items():
            with self.subTest(path=path):
                status, headers, _ = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertEqual(headers["Content-Type"], mime)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
                self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("GET", "/nope.js")[2], {"error": "Not found.", "code": "not_found"})
        for headers in ({"Origin": "https://example.com"}, {"Host": "attacker.example"}):
            with self.subTest(headers=headers):
                status, _, body = self.request("GET", "/api/catalog", headers=headers)
                self.assertEqual((status, body["code"]), (403, "forbidden"))

    def test_post_requires_token_and_rejects_foreign_origin(self):
        payload = json.dumps({"session": self.session()}).encode()
        for headers in ({"Content-Type": "application/json"},
                        {"Content-Type": "application/json", "X-Tuner-Token": self.catalog["token"], "Origin": "https://example.com"}):
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as error:
                urlopen(Request(self.url + "/api/export", payload, headers))
            self.assertEqual(error.exception.code, 403)
        headers = {"Content-Type": "application/json", "X-Tuner-Token": self.catalog["token"]}
        with urlopen(Request(self.url + "/api/export", payload, headers)) as response:
            self.assertEqual(json.load(response)["patch"], "")

    def test_malformed_posts_are_rejected(self):
        token = {"X-Tuner-Token": self.catalog["token"]}
        cases = (({"Content-Type": "text/plain"}, b"{}", 415, "unsupported_media_type"),
                 ({"Content-Type": "application/json"}, b"", 400, "bad_request"),
                 ({"Content-Type": "application/json", "Content-Length": str(MAX_BODY + 1)}, None, 400, "bad_request"),
                 ({"Content-Type": "application/json"}, b"{not json", 400, "bad_request"),
                 ({"Content-Type": "application/json"}, b"[1, 2]", 400, "bad_request"))
        for headers, body, status, code in cases:
            with self.subTest(headers=headers, body=body):
                got, _, reply = self.request("POST", "/api/preview", body, {**token, **headers})
                self.assertEqual((got, reply["code"]), (status, code))

    def test_catalog_reports_commit_and_composites(self):
        self.assertEqual(self.catalog["commit"], source_commit(ROOT))
        self.assertEqual(self.catalog["derived"]["ñ"], {"base": "n", "marks": ["tilde"]})

    def test_preview_round_trip_and_response_cache(self):
        payload = {"session": self.session(), "family": "P", "char": ".", "text": ".", "validate": False, "revision": 1}
        with mock.patch("tuner.serve.subprocess.run", wraps=subprocess.run) as worker:
            status, first = self.post(payload)
            payload.update(revision=2, session={**self.session(), "commit": HEX})
            again, second = self.post(payload)
        self.assertEqual((status, again), (200, 200), first)
        self.assertEqual(worker.call_count, 1)
        self.assertEqual(first, second)
        self.assertLessEqual({"before", "after", "bounds", "checks", "width", "family", "changed", "failures",
                              "warnings", "validation", "fill", "text_paths", "text_bounds", "text_gap"}, set(first))
        self.assertEqual(first["failures"], [])

    def test_busy_server_answers_409(self):
        self.assertTrue(self.server.busy.acquire(blocking=False))
        try:
            status, body = self.post({"session": self.session(), "family": "M", "char": "x", "text": "x"})
        finally:
            self.server.busy.release()
        self.assertEqual((status, body["code"]), (409, "busy"))

    def test_worker_errors_keep_their_code(self):
        report = subprocess.CompletedProcess([], 1, json.dumps({"error": "Base n: too round.", "code": "construction"}), "")
        with mock.patch("tuner.serve.subprocess.run", return_value=report):
            status, body = self.post({"session": self.session(), "family": "T", "char": "x", "text": "x"})
        self.assertEqual((status, body), (422, {"error": "Base n: too round.", "code": "construction"}))

    def test_worker_timeout_hides_local_paths(self):
        expired = subprocess.TimeoutExpired([sys.executable, "-m", "tuner.worker"], serve.WORKER_TIMEOUT)
        with mock.patch("tuner.serve.subprocess.run", side_effect=expired):
            status, body = self.post({"session": self.session(), "family": "P", "char": "y", "text": "y"})
        self.assertEqual((status, body["code"]), (504, "timeout"))
        self.assertNotIn(sys.executable, json.dumps(body))
        self.assertNotIn(str(ROOT), json.dumps(body))

    def test_stalled_request_is_dropped(self):
        self.assertLessEqual(Handler.timeout, 30)
        with mock.patch.object(Handler, "timeout", 0.3), socket.create_connection(("127.0.0.1", self.port), timeout=10) as s:
            s.sendall(b"GET /api/catalog HTTP/1.1\r\n")
            start = time.monotonic()
            self.assertEqual(s.recv(1024), b"")
            self.assertLess(time.monotonic() - start, 5)


class Startup(unittest.TestCase):
    def test_port_in_use_is_one_line(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen()
            port = busy.getsockname()[1]
            with self.assertRaises(SystemExit) as caught:
                serve.main(["--port", str(port), "--no-browser"])
        message = str(caught.exception.code)
        self.assertIn(f"port {port} is already in use", message)
        self.assertIn("--port", message)
        self.assertNotIn("\n", message)

    def test_permission_error_suggests_another_port(self):
        message = serve.bind_error(PermissionError(errno.EACCES, "Permission denied"), 80)
        self.assertIn("--port 8767", message)
        self.assertNotIn("\n", message)


if __name__ == "__main__":
    unittest.main()
