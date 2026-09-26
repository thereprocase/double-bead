"""Contribution safety and actual source → edited geometry → Git patch round trips."""
import ast
import copy
import functools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from beadjoint import charset, geom, glyphs, latin
from tuner.model import ACCENTS, FUNCTIONS, ROOT, SHARED, SOURCE_PATHS, Catalog, TunerError, number, source_commit
from tuner.serve import TunerServer

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
            if construction.required:
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
        expected = {("Base", "1"), ("Base", "w")} | ({("Mono", "w")} if hasattr(charset, "raw_m") else set())
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
               "_pointed_m": latin._pointed_m()}
        for name in ("extras", "mono_extras"):
            if hasattr(latin, name):
                out[name] = getattr(latin, name)()
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

    @unittest.skipUnless(hasattr(charset, "raw_m"), "needs charset.raw_m() from the font-code change")
    def test_every_mono_construction_is_what_the_fonts_use(self):
        raw = charset.raw_m()
        found = self.constructions("M")
        self.assertGreater(len(found), 20)
        for t, built in found:
            # glyphs.set_m softens the rebuilt glyphs before charset assembles Mono
            self.assertIn(raw[t["char"]].wkb, (built.wkb, geom.soft(built).wkb), f"Mono {t['char']}")

    def test_moved_constructions_become_required(self):
        for name in ("extras", "mono_extras"):
            with self.subTest(name=name):
                self.assertEqual(FUNCTIONS[name].required, hasattr(latin, name),
                                 f"latin.{name} exists now: make it required in tuner/model.py FUNCTIONS")

    @unittest.skipUnless(hasattr(latin, "extras") and hasattr(latin, "mono_extras"),
                         "needs latin.extras() and latin.mono_extras() from the font-code change")
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


class WorkerRuns(unittest.TestCase):
    def setUp(self):
        self.catalog = catalog()
        self.session = new_session()

    def target(self, char, group):
        return target(char, group)

    def test_edit_reaches_real_geometry_and_derived_accents(self):
        # Widen the right stem of n, preserving its width. This must flow into
        # accented n, Tab, and Mono's counter-widened n. Mono's rebuilt r stays put.
        for s in self.target("n", "Base")["slots"]:
            if s["label"].endswith(" x") and s["value"] == 6:
                self.session["values"][s["id"]] = 6.5
        request = {"session": self.session, "family": "P", "char": "n", "text": "n ñ ņ 0123", "validate": True}
        process = subprocess.run([sys.executable, "-m", "tuner.worker"], input=json.dumps(request),
                                 text=True, capture_output=True, cwd=ROOT, timeout=180)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertNotEqual(result["before"], result["after"])
        self.assertAlmostEqual(result["width"], 7.5, places=2)
        self.assertEqual(result["failures"], [])
        changed = {(g["family"], g["char"]) for g in result["changed"]}
        self.assertIn(("P", "ñ"), changed)
        self.assertIn(("T", "n"), changed)
        self.assertIn(("M", "n"), changed)
        self.assertNotIn(("M", "r"), changed)
        self.assertEqual(result["warnings"], [])
        self.assertFalse(result["fill"]["warn"])

    def test_closing_a_counter_warns_that_finishing_filled_it(self):
        # Right stem of n at x = 3.5 leaves a 0.5w slit; finishing fills it with ink, so the
        # glyph still passes the hard checks. The preview must say so rather than stay green.
        for s in self.target("n", "Base")["slots"]:
            if s["label"].endswith(" x") and s["value"] == 6:
                self.session["values"][s["id"]] = 3.5
        request = {"session": self.session, "family": "P", "char": "n", "text": "n", "validate": False}
        process = subprocess.run([sys.executable, "-m", "tuner.worker"], input=json.dumps(request),
                                 text=True, capture_output=True, cwd=ROOT, timeout=180)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertTrue(result["checks"]["ok"])
        self.assertTrue(result["fill"]["warn"])
        self.assertEqual(result["fill"]["before"], 0)
        self.assertGreater(result["fill"]["after"], 3)

    def test_fill_warning_follows_the_dotless_base_of_accented_i_and_j(self):
        # Marks above sit on dotless ı and ȷ: a new fill in ȷ must reach ĵ, and moving the
        # dot of i must not be charged to í (its geometry does not change).
        values = self.session["values"]
        for s in self.target("ȷ", "Specials")["slots"]:
            if s["label"] == "S1 point 3 y":
                values[s["id"]] = 10
        for s in self.target("i", "Base")["slots"]:
            if s["label"] == "D2 point 1 y":
                values[s["id"]] = -2.2
        self.assertEqual(len(values), 2)
        request = {"session": self.session, "family": "P", "char": "í", "text": "í ĵ", "validate": True}
        process = subprocess.run([sys.executable, "-m", "tuner.worker"], input=json.dumps(request),
                                 text=True, capture_output=True, cwd=ROOT, timeout=300)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertFalse(result["fill"]["warn"])
        self.assertIn("P:ȷ", result["warnings"])
        self.assertIn("P:ĵ", result["warnings"])
        self.assertNotIn("P:í", {g["family"] + ":" + g["char"] for g in result["changed"]})

    def test_fill_meter_covers_every_glyph(self):
        # Warnings rely on finished geometry reaching the Glyph records unchanged; a pipeline
        # change that breaks that would otherwise silence them without failing anything.
        script = ("from tuner.worker import FillMeter\n"
                  "meter = FillMeter()\n"
                  "from beadjoint import charset\n"
                  "for glyphs in (charset.full_p(), charset.full_mixed(), charset.full_m()):\n"
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
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_page_and_local_fonts_work_without_external_requests(self):
        for path in ("/", "/app.js", "/style.css", "/fonts/sans-400.woff2"):
            with self.subTest(path=path), urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_post_requires_token_and_rejects_foreign_origin(self):
        with urlopen(self.url + "/api/catalog") as response:
            c = json.load(response)
        payload = json.dumps({"session": {"schema": 1, "sources": c["sources"], "values": {}}}).encode()
        for headers in ({"Content-Type": "application/json"},
                        {"Content-Type": "application/json", "X-Tuner-Token": c["token"], "Origin": "https://example.com"}):
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as error:
                urlopen(Request(self.url + "/api/export", payload, headers))
            self.assertEqual(error.exception.code, 403)
        headers = {"Content-Type": "application/json", "X-Tuner-Token": c["token"]}
        with urlopen(Request(self.url + "/api/export", payload, headers)) as response:
            self.assertEqual(json.load(response)["patch"], "")


if __name__ == "__main__":
    unittest.main()
