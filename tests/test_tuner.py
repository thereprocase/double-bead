"""Contribution safety and actual source → edited geometry → Git patch round trips."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tuner.model import Catalog, ROOT
from tuner.serve import TunerServer


class SourceEditing(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()
        self.session = {"schema": 1, "sources": self.catalog.hashes, "values": {}}

    def target(self, char, group):
        return next(t for t in self.catalog.targets if t["char"] == char and t["group"] == group)

    def test_noop_produces_no_patch(self):
        self.assertEqual(self.catalog.patch(self.session), "")

    def test_signed_numeric_edit_preserves_the_rest_of_the_source(self):
        slot = next(s for s in self.target("b", "Base")["slots"] if s["value"] == -4)
        self.session["values"][slot["id"]] = -3.75
        edited = self.catalog.edited_sources(self.session)[slot["path"]]
        original = self.catalog.sources[slot["path"]]
        self.assertEqual(edited, original[:slot["start"]] + b"-3.75" + original[slot["end"]:])

    def test_unicode_column_offsets_and_patch_apply(self):
        slot = self.target("Ω", "Mono")["slots"][0]
        self.session["values"][slot["id"]] = slot["value"] + .1
        patch = self.catalog.patch(self.session)
        subprocess.run(["git", "apply", "--check", "-"], input=patch, text=True, cwd=ROOT, check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in self.catalog.sources.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(source)
            subprocess.run(["git", "apply", "-"], input=patch, text=True, cwd=root, check=True, capture_output=True)
            for name, expected in self.catalog.edited_sources(self.session).items():
                self.assertEqual((root / name).read_bytes(), expected)

    def test_rejects_code_nonfinite_out_of_range_and_unknown_slots(self):
        slot = self.target("a", "Base")["slots"][0]
        for value in ("__import__('os')", float("nan"), float("inf"), True, 100):
            self.session["values"] = {slot["id"]: value}
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.catalog.edited_sources(self.session)
        self.session["values"] = {"../../other.py:1:0": 1}
        with self.assertRaises(ValueError):
            self.catalog.edited_sources(self.session)

    def test_rejects_stale_session_and_changed_disk_source(self):
        stale = copy.deepcopy(self.session)
        stale["sources"]["beadjoint/glyphs.py"] = "old"
        with self.assertRaises(ValueError):
            self.catalog.patch(stale)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in self.catalog.sources.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(source)
            c = Catalog(root)
            (root / "beadjoint/glyphs.py").write_bytes(b"# changed")
            with self.assertRaises(ValueError):
                c.patch(self.session)

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
