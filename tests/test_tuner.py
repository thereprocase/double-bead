"""Contribution safety and actual source → edited geometry → Git patch round trips."""
import ast
import contextlib
import copy
import errno
import functools
import http.client
import io
import json
import math
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from beadjoint import charset, geom, glyphs, latin, setting, verify
from tuner import serve
from tuner.model import (ACCENTS, COMMIT, FUNCTIONS, ROOT, SHARED, SOURCE_PATHS, Catalog, TunerError, number,
                         source_commit)
from tuner.serve import MAX_BODY, Handler, TunerServer
from tuner.worker import (CACHE_ENV, CACHE_SECRET_ENV, Beadjoint, FinishedCache, absent, check_message, checks,
                          explain, fill_change, finite, finishing_fingerprint, options)

HEX = "0123456789abcdef0123456789abcdef01234567"
TEST_SECRET = "5e" * 32     # a fixed per-test-run cache secret; the server draws a random one
# Child processes exchange text as UTF-8 and have a deadline. Text pipes default to the ANSI code page
# on Windows (cp1252 has no Ĳ), and on Python 3.14 an encoding error there kills the thread feeding
# stdin, so the child waits for input until the job is cancelled. Child Pythons are told to write UTF-8.
CHILD_TIMEOUT = 120     # s; these children take seconds, the limit turns a hang into a failure
UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


@functools.cache
def catalog():
    """The full catalog, built once: tests only read it."""
    return Catalog()


def copy_sources(root, paths=None):
    """Copy the editable sources (or every file a preview reads) under root."""
    for name in paths or catalog().sources:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(catalog().inputs[name])


def target(char, group):
    return next(t for t in catalog().targets if t["char"] == char and t["group"] == group)


def slot(char, group, label):
    return next(s for s in target(char, group)["slots"] if s["label"] == label)


def new_session():
    return {"schema": 1, "sources": dict(catalog().hashes), "values": {}}


def worker_env(directory=None):
    """The environment the server gives its workers: a cache directory and its secret, or neither."""
    env = {k: v for k, v in os.environ.items() if k not in (CACHE_ENV, CACHE_SECRET_ENV)}
    if directory:
        env.update({CACHE_ENV: directory, CACHE_SECRET_ENV: TEST_SECRET})
    return env


def run_worker(request, env=None, timeout=300):
    process = subprocess.run([sys.executable, "-m", "tuner.worker"], input=json.dumps(request), encoding="utf-8",
                             capture_output=True, cwd=ROOT, timeout=timeout, env=env or worker_env())
    return process, json.loads(process.stdout)


def git(root, *args):
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c", "user.name=repro",
                           "-c", "user.email=repro@local", *args], cwd=root, capture_output=True, encoding="utf-8",
                          check=True, timeout=CHILD_TIMEOUT)


def build_error(values):
    """explain() for the exception _raw_p raises with edits to glyphs.py, compiled as the worker does."""
    session = new_session()
    session["values"].update(values)
    source = catalog().edited_sources(session)["beadjoint/glyphs.py"]
    namespace = {"__name__": "beadjoint.edited_for_test", "__package__": "beadjoint"}
    exec(compile(source, "beadjoint/glyphs.py", "exec"), namespace)
    try:            # not assertRaises: it drops the traceback that locates the construction
        namespace["_raw_p"]()
    except ValueError as exc:
        return explain(exc, catalog())
    raise AssertionError("the edited glyphs should not build")


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

    def git_apply(self, patch, root, *options):
        # The bytes the browser saves: a text pipe would encode the patch in the ANSI code page on
        # Windows and turn its LF line endings into CRLF, which no longer matches the sources.
        process = subprocess.run(["git", "apply", *options, "-"], input=patch.encode("utf-8"), cwd=root,
                                 capture_output=True, timeout=CHILD_TIMEOUT)
        self.assertEqual(process.returncode, 0, process.stderr.decode("utf-8", "replace"))

    def assert_patch_applies(self, patch):
        self.git_apply(patch, ROOT, "--check")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root)
            # A repository with this one's attributes, so git writes the sources as it would in a clone:
            # Git for Windows defaults to core.autocrlf=true, and .gitattributes keeps Python sources LF.
            shutil.copyfile(ROOT / ".gitattributes", root / ".gitattributes")
            git(root, "init", "-q")
            self.git_apply(patch, root)
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
        # 10**400 would overflow math.isfinite; it must be refused like any other out-of-range value.
        for value in ("__import__('os')", float("nan"), float("inf"), True, 100, 10 ** 400, -10 ** 400):
            self.session["values"] = {s["id"]: value}
            with self.subTest(value=str(value)[:20]), self.assertRaises(TunerError) as caught:
                self.catalog.edited_sources(self.session)
            self.assertEqual(caught.exception.code, "bad_session")
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

    def test_any_module_a_preview_reads_counts_as_a_source_change(self):
        # verify.LINE_MIN is not an editable file, but changing it changes every check.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root, catalog().inputs)
            c = Catalog(root, families=False)
            c.assert_fresh()
            path = root / "beadjoint/verify.py"
            path.write_bytes(path.read_bytes().replace(b"LINE_MIN = 1.98", b"LINE_MIN = 2.5"))
            with self.assertRaisesRegex(TunerError, "beadjoint/verify.py changed on disk"):
                c.assert_fresh()
            (root / "beadjoint/verify.py").unlink()
            with self.assertRaisesRegex(TunerError, "beadjoint/verify.py changed"):
                c.assert_fresh()

    def test_every_module_the_worker_imports_is_watched(self):
        script = ("import sys\nfrom tuner.worker import Beadjoint\nBeadjoint()\n"
                  "print('\\n'.join(m.__file__ for n, m in sys.modules.items() if n.split('.')[0] in ('beadjoint', 'tuner')))")
        process = subprocess.run([sys.executable, "-c", script], encoding="utf-8", capture_output=True, cwd=ROOT, check=True,
                                 env=UTF8_ENV, timeout=CHILD_TIMEOUT)
        imported = {Path(f).resolve().relative_to(ROOT).as_posix() for f in process.stdout.split()}
        self.assertIn("beadjoint/setting.py", imported)
        self.assertLessEqual(imported, set(catalog().inputs))


class SourceCommit(unittest.TestCase):
    def test_this_checkout(self):
        paths = [p for p in catalog().inputs if p.startswith("beadjoint/")]
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, encoding="utf-8",
                              timeout=CHILD_TIMEOUT).stdout.strip()
        clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *paths], cwd=ROOT, timeout=CHILD_TIMEOUT).returncode == 0
        self.assertEqual(source_commit(ROOT, paths), head if clean else None)
        self.assertIsNone(source_commit(ROOT / "beadjoint", ["glyphs.py"]), "root must be the top of the checkout")

    def test_only_a_clean_tracked_checkout_at_root_names_a_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            # A non-ASCII checkout path: git reports it in UTF-8, which the Windows code page misreads.
            root = Path(directory, "Łĳ")
            root.mkdir()
            paths = ["beadjoint/glyphs.py", "beadjoint/verify.py"]
            copy_sources(root, paths)
            self.assertIsNone(source_commit(root, paths), "not a Git checkout")
            git(root, "-c", "init.defaultBranch=main", "init", "-q")
            git(root, "add", "beadjoint/glyphs.py")
            git(root, "commit", "-q", "-m", "sources")
            self.assertIsNone(source_commit(root, paths), "verify.py is untracked")
            git(root, "add", "beadjoint/verify.py")
            git(root, "commit", "-q", "-m", "verify")
            commit = source_commit(root, paths)
            self.assertRegex(commit, COMMIT)
            self.assertEqual(commit, git(root, "rev-parse", "HEAD").stdout.strip())
            (root / "beadjoint/verify.py").write_text("LINE_MIN = 2.5\n")
            self.assertIsNone(source_commit(root, paths), "uncommitted change")


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

    def changed(self, path, old, new):
        """The catalog of the sources with one replacement in path."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root)
            source = (root / path).read_bytes()
            self.assertIn(old, source)
            (root / path).write_bytes(source.replace(old, new, 1))
            return Catalog(root, families=False)

    def test_reassignment_keeps_the_last_live_definition(self):
        # Python keeps the last assignment. One that reads the earlier value keeps it live; one
        # that does not leaves it dead, and its numbers would change nothing.
        head = b"    head = D((1.7, -2.6), 1.4) | S((1.7, -2.6), (0.7, 0.4, B))"
        original = target("’", "Shared punctuation")
        kept = self.changed("beadjoint/latin.py", head, head + b"\n    head = head")
        quote = [t for t in kept.targets if t["group"] == "Shared punctuation" and t["char"] == "’"]
        self.assertEqual([(t["line"], len(t["slots"])) for t in quote], [(original["line"], len(original["slots"]))])
        replaced = self.changed("beadjoint/latin.py", head, head + b"\n    head = D((1.7, -2.6), 1.2)")
        quote = [t for t in replaced.targets if t["group"] == "Shared punctuation" and t["char"] == "’"]
        self.assertEqual([(t["line"], [s["value"] for s in t["slots"]]) for t in quote],
                         [(original["line"] + 1, [1.7, -2.6, 1.2])])
        self.assertNotIn(original["slots"][0]["id"], replaced.slots)
        n = b'    g["n"] = S((1, 10), (1, 1, 0), (6, 1), (6, 10))'
        for extra, line in ((b'\n    g["n"] = S((1, 10), (6, 10))', 1), (b'\n    g["n"] = shift(g["n"], 0.5)', 0)):
            with self.subTest(extra=extra):
                c = self.changed("beadjoint/glyphs.py", n, n + extra)
                lines = [t["line"] for t in c.targets if (t["group"], t["char"]) == ("Base", "n")]
                self.assertEqual(lines, [target("n", "Base")["line"] + line])

    def test_a_construction_defined_in_two_files_stops_the_tuner(self):
        self.assert_refused("beadjoint/glyphs.py", b"def _raw_one_tabular():",
                            b"def square_w():\n    return S((1, 0), (1, 9))\n\n\ndef _raw_one_tabular():",
                            "square_w() is defined in both beadjoint/glyphs.py and beadjoint/latin.py")
        self.assert_refused("beadjoint/marks.py", b"\nABOVE_LOW, ", b"\nDOT = 2\nABOVE_LOW, ",
                            "DOT is defined in both beadjoint/marks.py and beadjoint/geom.py")

    def test_constructions_without_literal_numbers_stop_the_tuner(self):
        self.assert_refused("beadjoint/latin.py", b"def square_w():", b"def square_w():\n    return None\n\n\ndef _w():",
                            "square_w()")
        self.assert_refused("beadjoint/geom.py", b"\nDOT = 1.5 ", b"\nDOT = 3 / 2 ", "no literal numbers the tuner can edit: DOT")
        self.assert_refused("beadjoint/latin.py", b"frac_slash = diagonal(0.9, 10, 4.9, -4)", b"frac_slash = diagonal(*FRAC)",
                            "frac_slash in symbols()")
        self.assert_refused("beadjoint/marks.py", b'"grave": S((0, 0, B), (2.2, 2.4, B)),', b'"grave": S(*GRAVE),',
                            "marks.SHAPES['grave']")

    def test_replaced_constructions_are_dropped(self):
        c = catalog()
        expected = {("Base", "1"), ("Base", "w"), ("Mono", "w")}
        self.assertEqual(set(c.superseded), expected)
        for group, char in expected:
            self.assertFalse([t for t in c.targets if (t["group"], t["char"]) == (group, char)])
        self.assertTrue([t for t in c.targets if (t["group"], t["char"]) == ("Footed 1", "1")])
        self.assertTrue([t for t in c.targets if (t["group"], t["char"]) == ("Shared w", "w")])

    @staticmethod
    def raw_outputs():
        """Each construction function's output, called as charset calls it (independent of tuner/model.py)."""
        p = glyphs._raw_p()
        cap, sym = latin.capitals(), latin.symbols(p)
        return {"_raw_p": p, "capitals": cap, "symbols": sym, "specials": latin.specials(p, cap, sym),
                "mono_narrow": latin.mono_narrow(), "_raw_m_rebuilt": glyphs._raw_m_rebuilt(),
                "_raw_one_tabular": glyphs._raw_one_tabular(), "square_w": latin.square_w(),
                "_pointed_m": latin._pointed_m(), "extras": latin.extras(), "mono_extras": latin.mono_extras()}

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
        self.assertEqual((bj.tab_cell, bj.tab_digit), (setting.CELL_F, setting.FIGURE_MAX))
        self.assertEqual(bj.max_thickness, verify.SHIPPED_MAX_T)
        self.assertAlmostEqual(bj.tab_digit, 7.02)

    def test_fill_warning_threshold(self):
        limit = Beadjoint().fill_warn
        m = self.Meter
        self.assertFalse(fill_change(m(1.0), None, m(1.0 + limit), None, limit)[2])
        self.assertTrue(fill_change(m(1.0), None, m(1.0 + limit + 1e-6), None, limit)[2])
        self.assertEqual(fill_change(m(None), None, m(5.0), None, limit), (None, None, False))

    def test_absent_glyphs_are_explained_per_family(self):
        bj = Beadjoint()
        self.assertEqual(absent(bj, "M", ["©"]), "Mono doesn't include ©: wider than Mono's 10w limit.")
        self.assertEqual(absent(bj, "P", ["x"]), "Proportional doesn't include x.")

    def test_request_characters(self):
        bj = Beadjoint()
        for request in ({"char": "\x07"}, {"char": "\ud800"}, {"char": "\x85"}, {"text": "a\x7fb"}, {"text": "a\u0000"}):
            with self.subTest(request=request), self.assertRaises(TunerError) as caught:
                options(request, bj)
            self.assertEqual(caught.exception.code, "bad_request")
        with self.assertRaises(TunerError) as caught:
            options({"char": "‮"}, bj)
        self.assertEqual(str(caught.exception), "Fillaprint has no glyph for U+202E.", "invisible characters by code only")
        self.assertEqual(options({"char": "ñ", "text": "a b"}, bj), ("P", "ñ", "a b", False))

    def test_check_messages_name_what_the_build_would_reject(self):
        bj = Beadjoint()
        report = {"thickness": 5.5, "thin": [], "islands": [], "piece_gap": None, "fused": True}
        self.assertEqual(check_message("ĳ (Proportional)", report, bj),
                         "ĳ (Proportional): finishing joined separate pieces — keep them at least 1.98w apart; "
                         "it is 5.5w thick at its thickest; the fonts allow at most 4.85w.")
        report.update(thickness=2.8, fused=False, piece_gap=1.5)
        self.assertEqual(check_message("x (Mono)", report, bj),
                         "x (Mono): separate pieces are only 1.5w apart (at least 1.98w).")

    def test_ink_over_the_shipped_maximum_fails_on_its_own(self):
        bj = Beadjoint()
        report = checks(geom.D((0, 0), 3), bj, "● (Proportional)")      # a 6w blob in one piece
        self.assertGreater(report["thickness"], bj.max_thickness)
        self.assertEqual((report["fused"], report["ok"]), (False, False))
        self.assertEqual(check_message("● (Proportional)", report, bj),
                         f"● (Proportional): it is {report['thickness']:g}w thick at its thickest; the fonts allow at most 4.85w.")
        self.assertTrue(checks(geom.D((0, 0), 2), bj, "• (Proportional)")["ok"], "the 4w bullet is within the limit")

    def test_pieces_closer_than_the_line_gap_fail_on_their_own(self):
        bj = Beadjoint()
        report = checks(geom.D((0, 0), 1) | geom.D((3.5, 0), 1), bj, "x (Proportional)")     # two 2w dots, 1.5w apart
        self.assertEqual((report["piece_gap"], report["fused"], report["ok"]), (1.5, False, False))
        self.assertEqual(check_message("x (Proportional)", report, bj),
                         "x (Proportional): separate pieces are only 1.5w apart (at least 1.98w).")
        self.assertTrue(checks(geom.D((0, 0), 1) | geom.D((4, 0), 1), bj, "x (Proportional)")["ok"], "2w apart passes")

    def test_construction_errors_name_the_construction(self):
        message = build_error({slot("n", "Base", "S1 point 2 corner radius")["id"]: 8})
        self.assertEqual(message, "n (Base): the rounded corners at (1, 1) and (6, 1) together need 9w of a segment "
                                  "only 5w long. Reduce the corner radius or lengthen the segment.")
        message = build_error({slot("n", "Base", "S1 point 3 x")["id"]: 1})
        self.assertEqual(message, "n (Base): the point at (1, 1) sits on the point next to it, so the stroke has no "
                                  "direction there. Move one of them.")

    def test_other_errors_have_plain_messages(self):
        for exc in (ZeroDivisionError("float division by zero"), RuntimeError("GEOS: TopologyException"),
                    ValueError("solve: target not bracketed")):
            message = explain(exc, catalog())
            with self.subTest(exc=exc):
                self.assertTrue(message.startswith("The edited glyph sources"))
                self.assertNotIn(type(exc).__name__, message)
                self.assertNotIn(str(exc), message)

    def test_non_finite_numbers_become_null(self):
        with contextlib.redirect_stderr(io.StringIO()) as log:
            self.assertEqual(finite({"a": [1.5, math.nan], "b": (math.inf,), "c": "nan"}), {"a": [1.5, None], "b": [None], "c": "nan"})
        self.assertIn("result.a[1]", log.getvalue())

    def test_finishing_fingerprint(self):
        fingerprint = finishing_fingerprint(geom)
        script = "from beadjoint import geom\nfrom tuner.worker import finishing_fingerprint\nprint(finishing_fingerprint(geom).hex())"
        for seed in ("1", "2"):      # constants that are sets must not make it vary between workers
            process = subprocess.run([sys.executable, "-c", script], encoding="utf-8", capture_output=True, cwd=ROOT, check=True,
                                     env={**UTF8_ENV, "PYTHONHASHSEED": seed}, timeout=CHILD_TIMEOUT)
            self.assertEqual(process.stdout.strip(), fingerprint.hex())
        source = catalog().sources["beadjoint/geom.py"]

        def compiled(old, new):
            self.assertIn(old, source)
            module = types.ModuleType("geom_under_test")
            exec(compile(source.replace(old, new), "beadjoint/geom.py", "exec"), module.__dict__)
            return finishing_fingerprint(module)

        self.assertEqual(compiled(b"DOT = 1.5 ", b"DOT = 1.25 "), fingerprint, "an edited dot radius keeps the cache")
        self.assertNotEqual(compiled(b"PINCH_R = 0.98", b"PINCH_R = 0.97"), fingerprint)
        self.assertNotEqual(compiled(b"return soft(fillet_inside(fill_pinches(g)))", b"return soft(fill_pinches(g))"),
                            fingerprint)


class GlyphCache(unittest.TestCase):
    SECRET = bytes.fromhex(TEST_SECRET)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = directory.name
        self.shape = geom.D((0, 0), 2)
        self.key = FinishedCache.key(b"fingerprint", self.shape)

    def saved(self, *entries):
        cache = FinishedCache(self.dir, self.SECRET)
        for key, area, wkb, persist in entries:
            cache.put(key, area, wkb, persist)
        cache.save()
        return Path(self.dir, "finished-v2.bin")

    def test_round_trip(self):
        volatile = FinishedCache.key(b"fingerprint", geom.D((5, 5)))
        self.saved((self.key, 0.25, self.shape.wkb, True), (volatile, 1.0, geom.D((5, 5)).wkb, False))
        area, shape = FinishedCache(self.dir, self.SECRET).get(self.key)
        self.assertEqual((area, shape.wkb), (0.25, self.shape.wkb))
        self.assertIsNone(FinishedCache(self.dir, self.SECRET).get(volatile), "edited results stay in memory")
        self.assertNotEqual(FinishedCache.key(b"other finishing", self.shape), self.key)

    def test_records_are_authenticated(self):
        path = self.saved((self.key, 0.25, self.shape.wkb, True))
        self.assertIsNone(FinishedCache(self.dir, b"another secret, another run").get(self.key))
        self.assertEqual(FinishedCache(self.dir, None).entries, {}, "no secret: the file is not read")
        self.assertIsNone(FinishedCache(None, self.SECRET).path, "no directory: nothing is written")
        data = bytearray(path.read_bytes())
        data[60] ^= 1           # one bit of the stored geometry
        path.write_bytes(data)
        self.assertIsNone(FinishedCache(self.dir, self.SECRET).get(self.key))

    def test_damaged_files_are_ignored(self):
        path = self.saved((self.key, 0.25, self.shape.wkb, True))
        good = path.read_bytes()
        for tail in (good[:-10], struct_record(b"\x01" * 32, 0.5, 10 ** 9), b"\x00" * 7):
            path.write_bytes(good + tail)
            with self.subTest(tail=tail[:8]):
                cache = FinishedCache(self.dir, self.SECRET)
                self.assertEqual(list(cache.entries), [self.key], "the intact record is kept")
        path.write_bytes(good[:-1])
        self.assertEqual(FinishedCache(self.dir, self.SECRET).entries, {})

    def test_a_cache_over_the_size_limit_is_not_written(self):
        # _load ignores files over the limit, so writing one would leave every later worker cold.
        path = self.saved((self.key, 0.25, self.shape.wkb, True))
        loadable = path.read_bytes()
        cache = FinishedCache(self.dir, self.SECRET)
        large = geom.D((9, 9), 5)
        key = FinishedCache.key(b"fingerprint", large)
        cache.put(key, 1.0, large.wkb, persist=True)
        with mock.patch("tuner.worker.MAX_CACHE_BYTES", len(loadable) + 100), \
                contextlib.redirect_stderr(io.StringIO()) as log:
            cache.save()
            self.assertEqual(path.read_bytes(), loadable, "the previous file stays")
            self.assertEqual(list(FinishedCache(self.dir, self.SECRET).entries), [self.key])
        self.assertEqual(cache.get(key)[1].wkb, large.wkb, "this worker keeps the entry")
        self.assertIn("was not saved", log.getvalue())

    def test_a_record_that_does_not_parse_is_a_miss(self):
        self.saved((self.key, 0.25, b"not geometry", True))
        cache = FinishedCache(self.dir, self.SECRET)
        self.assertIn(self.key, cache.entries)
        self.assertIsNone(cache.get(self.key))
        self.assertNotIn(self.key, cache.entries)


def struct_record(key, area, size):
    from tuner.worker import _RECORD
    return _RECORD.pack(key, area, size)


class WorkerRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # One glyph cache for these runs, as the server shares one between its workers: the first
        # run finishes the unedited font and later ones read it back.
        cls.cache = tempfile.mkdtemp(prefix="fillaprint-tuner-test-")
        cls.env = worker_env(cls.cache)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cache, ignore_errors=True)

    def setUp(self):
        self.session = new_session()

    def edit(self, char, group, labels, value):
        for label in labels:
            self.session["values"][slot(char, group, label)["id"]] = value

    def run_ok(self, family, char, text, validate):
        request = {"session": self.session, "family": family, "char": char, "text": text, "validate": validate}
        process, result = run_worker(request, self.env)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        return result

    def test_edit_reaches_real_geometry_and_derived_accents(self):
        # Widen the right stem of n, preserving its width. This must flow into
        # accented n, Tab, and Mono's counter-widened n. Mono's rebuilt r stays put.
        self.edit("n", "Base", ("S1 point 3 x", "S1 point 4 x"), 6.5)
        result = self.run_ok("P", "n", "n ñ ņ 0123", True)
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
        process, result = run_worker(request, worker_env())
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertTrue(result["checks"]["ok"])
        self.assertTrue(result["fill"]["warn"])
        self.assertEqual(result["fill"]["before"], 0)
        self.assertGreater(result["fill"]["after"], 3)
        # The first cached run stores the unedited font; the second reads it back.
        with tempfile.TemporaryDirectory() as directory:
            for _ in range(2):
                process, cached = run_worker(request, worker_env(directory))
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(cached, result)
            self.assertEqual(os.listdir(directory), ["finished-v2.bin"])

    def test_cache_hits_keep_their_fill(self):
        # Ń is N (5.77 w² of fill in its acute joins) plus an acute. After an acute edit N is read
        # back from the cache; its recorded fill must come with it, or Ń would seem to lose it.
        self.edit("á", "Accent acute", ("S1 point 1 x",), 0.2)
        fill = self.run_ok("P", "Ń", "Ń", False)["fill"]
        self.assertGreater(fill["before"], 5)
        self.assertEqual(fill, {"before": fill["before"], "after": fill["before"], "warn": False})

    def test_fill_warning_follows_the_dotless_base_of_accented_i_and_j(self):
        # Marks above sit on dotless ı and ȷ: a new fill in ȷ must reach ĵ, and moving the
        # dot of i must not be charged to í (its geometry does not change).
        self.edit("ȷ", "Specials", ("S1 point 3 y",), 10)
        self.edit("i", "Base", ("D2 point 1 y",), -2.2)
        result = self.run_ok("P", "í", "í ĵ", True)
        self.assertFalse(result["fill"]["warn"])
        self.assertIn("P:ȷ", result["warnings"])
        self.assertIn("P:ĵ", result["warnings"])
        self.assertNotIn("P:í", {g["family"] + ":" + g["char"] for g in result["changed"]})

    def test_validation_reports_every_failure(self):
        # n at 8.5w no longer fits Mono (its widened form is 10.5w), and a 8.5w 0 overflows Tab's
        # 9w digit cell. Both must be reported in one run, as objects the page can act on.
        self.edit("n", "Base", ("S1 point 3 x", "S1 point 4 x"), 7.5)
        self.edit("0", "Base", ("So1 point 2 x", "So1 point 3 x"), 7.5)
        result = self.run_ok("P", "n", "n0", True)
        for f in result["failures"]:
            self.assertEqual(set(f), {"family", "char", "code", "message"})
            self.assertNotIn("Beadjoint", f["message"])
        failures = {(f["family"], f["char"], f["code"]): f["message"] for f in result["failures"]}
        self.assertLessEqual({("M", c, "disappeared") for c in "nñńņň"}, set(failures))
        self.assertIn("(10.50w) than Mono's 10w limit", failures["M", "n", "disappeared"])
        self.assertIn(("T", "0", "tabular_width"), failures)
        changed = {(g["family"], g["char"]): g for g in result["changed"]}
        self.assertEqual(changed["M", "ñ"], {"family": "M", "char": "ñ", "checks": None, "fill_warn": False,
                                             "failed": True, "disappeared": True})
        self.assertTrue(changed["T", "0"]["failed"])
        self.assertFalse(changed["P", "0"]["failed"])

    def test_a_family_that_fails_to_build_does_not_stop_the_others(self):
        self.edit("Ω", "Mono", ("S1 point 5 corner radius",), 8)
        self.edit("b", "Base", ("S2 point 2 x", "S2 point 3 x"), 6.5)
        result = self.run_ok("P", "b", "b", True)
        failures = {(f["family"], f["char"], f["code"]): f["message"] for f in result["failures"]}
        self.assertEqual(list(failures), [("M", "Ω", "error")])
        self.assertTrue(failures["M", "Ω", "error"].startswith("Ω (Mono): the rounded corners"))
        changed = {(g["family"], g["char"]) for g in result["changed"]}
        self.assertLessEqual({("P", "b"), ("T", "b")}, changed)
        self.assertFalse([c for c in changed if c[0] == "M"])

    def test_pieces_joined_by_finishing_fail_as_in_the_build(self):
        # ĳ is i and j set side by side (latin.specials shifts j by 2.5). Moving j 1.5w left puts
        # the stems 1.5w apart, as v0.1.1's shift of 1 did: finishing fills the slit into a 5.5w
        # slab. The build rejects that in every family, so validation must too. j itself changes
        # but stays sound, and Mono's k keeps its designed join (verify.FUSED_BY_DESIGN).
        self.edit("j", "Base", ("S1 point 1 x", "S1 point 2 x", "D2 point 1 x"), 2.5)
        self.edit("k", "Mono", ("S2 point 1 x",), 7.9)
        result = self.run_ok("P", "ĳ", "ĳ", True)
        self.assertTrue(result["checks"]["fused"])
        self.assertFalse(result["checks"]["ok"])
        self.assertFalse(result["fill"]["warn"], "joined pieces fail; the amber warning is for fill that does not join")
        failures = {(f["family"], f["char"], f["code"]): f["message"] for f in result["failures"]}
        for family, name in (("P", "Proportional"), ("T", "Tab"), ("M", "Mono")):
            self.assertEqual(failures[family, "ĳ", "checks"],
                             f"ĳ ({name}): finishing joined separate pieces — keep them at least 1.98w apart; "
                             "it is 5.5w thick at its thickest; the fonts allow at most 4.85w.")
        changed = {(g["family"], g["char"]): g for g in result["changed"]}
        self.assertFalse(changed["P", "j"]["failed"])
        self.assertEqual((changed["M", "k"]["failed"], changed["M", "k"]["checks"]["fused"]), (False, False))
        self.assertNotIn("P:ĳ", result["warnings"])

    def test_emptied_glyphs_are_reported_not_fatal(self):
        # A dot radius of 0 is in range and empties the period. Its bounds are NaN, which would
        # break the preview line and JSON; it must be reported instead, as "no ink", not "too wide".
        self.session["values"][target(".", "Global dot radius")["slots"][0]["id"]] = 0
        result = self.run_ok("P", "a", "a.", True)
        failures = {(f["family"], f["char"], f["code"]): f["message"] for f in result["failures"]}
        # Every emptied glyph is reported, not only the first one validation reaches.
        self.assertLessEqual({("P", c, "checks") for c in ".:·…"}, set(failures))
        self.assertEqual(failures["P", ".", "checks"], ". (Proportional): the edit leaves no ink to print.")
        self.assertEqual(failures["M", ".", "disappeared"], "Mono leaves out .: after this edit it has no ink to print.")
        self.assertEqual(len(result["text_paths"]), 1, "the empty period is left out of the preview line")
        changed = {(g["family"], g["char"]): g for g in result["changed"]}
        self.assertEqual((changed["P", "."]["checks"], changed["P", "."]["failed"]), (None, True))

    def test_a_glyph_an_edit_fits_into_mono_can_be_previewed(self):
        self.edit("©", "Symbols", ("So1 point 2 x", "So1 point 3 x"), 9)
        result = self.run_ok("M", "©", "a©", False)
        self.assertEqual(result["before"], "", "Mono had no © before the edit")
        self.assertAlmostEqual(result["width"], 10, places=2)

    def test_request_errors_are_plain(self):
        for request, code, text in (({"family": "X"}, "bad_request", "Proportional, Tab or Mono"),
                                    ({"char": "\x07"}, "bad_request", "Choose one character"),
                                    ({"char": "Ж"}, "no_glyph", "Fillaprint has no glyph for Ж"),
                                    ({"text": "Пa"}, "text_glyphs", "Fillaprint has no glyph for П"),
                                    ({"family": "M", "char": "©"}, "not_in_family", "Mono doesn't include ©: wider")):
            process, result = run_worker({"session": self.session, **request}, self.env)
            with self.subTest(code=code):
                self.assertEqual(process.returncode, 1)
                self.assertEqual(result["code"], code)
                self.assertIn(text, result["error"])
                self.assertNotIn("Beadjoint", result["error"])

    def test_fill_meter_covers_every_glyph(self):
        # Warnings rely on finished geometry reaching the Glyph records unchanged; a pipeline
        # change that breaks that would otherwise silence them without failing anything. The
        # fused-pieces check reads the meter's record of what finishing received, which must be
        # exactly what the build checks (charset.finish_inputs).
        script = ("from tuner.worker import Beadjoint, FillMeter\n"
                  "bj = Beadjoint()\n"
                  "meter = FillMeter(bj)\n"
                  "families = {'P': bj.charset.full_p(), 'T': bj.charset.full_mixed(), 'M': bj.charset.full_m()}\n"
                  "inputs = bj.charset.finish_inputs()\n"
                  "for name, glyphs in families.items():\n"
                  "    missing = [c for c, g in glyphs.items() if meter.filled(g.geom) is None]\n"
                  "    assert not missing, missing\n"
                  "    other = [c for c, g in glyphs.items() if meter.finish_input(g.geom) is not inputs[name][c]]\n"
                  "    assert not other, (name, other)\n"
                  "    assert meter.filled(glyphs['N'].geom) > 1, 'acute joins are filled by design'\n"
                  "    for accented, base in (('í', 'ı'), ('ĵ', 'ȷ'), ('ñ', 'n')):\n"
                  "        assert meter.finished[id(glyphs[accented].geom)][2] is glyphs[base].geom, accented\n")
        process = subprocess.run([sys.executable, "-c", script], encoding="utf-8", capture_output=True, cwd=ROOT, timeout=300,
                                 env=UTF8_ENV)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


@contextlib.contextmanager
def serving(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def http_request(port, method, path, body=None, headers=()):
    """(status, headers, parsed body) without urllib adding or checking anything."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        conn.request(method, path, body=body, headers=dict(headers))
        response = conn.getresponse()
        data = response.read()
        json_body = response.headers.get_content_type() == "application/json" and data
        return response.status, response.headers, json.loads(data) if json_body else data
    finally:
        conn.close()


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
        return http_request(self.port, method, path, body, headers)

    def post(self, payload, path="/api/preview"):
        headers = {"Content-Type": "application/json", "X-Tuner-Token": self.catalog["token"]}
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        status, _, reply = self.request("POST", path, body, headers)
        return status, reply

    def test_port_cannot_be_taken_over(self):
        # A socket that asks to share the port must not get it: on Windows SO_REUSEADDR would let it bind
        # the listening tuner's port and receive its connections, tokens included.
        with socket.socket() as other:
            other.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            with self.assertRaises(OSError):
                other.bind(("127.0.0.1", self.port))

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

    def test_other_methods_and_malformed_requests_answer_json(self):
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS", "BREW"):
            with self.subTest(method=method):
                status, headers, body = self.request(method, "/api/preview")
                self.assertEqual((status, body["code"]), (405, "method_not_allowed"))
                self.assertEqual(headers["Allow"], "GET, POST")
                self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        status, headers, body = self.request("HEAD", "/")
        self.assertEqual((status, headers["Allow"], body), (405, "GET, POST", b""))
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as s:
            s.sendall(b"GET / HTTP/1.1\r\n" + b"X-Many: header\r\n" * 101 + b"\r\n")
            reply = b""
            while chunk := s.recv(4096):
                reply += chunk
        head, _, body = reply.partition(b"\r\n\r\n")
        self.assertTrue(head.startswith(b"HTTP/1.0 431 "), head)
        self.assertEqual(json.loads(body)["code"], "bad_request")

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
                 ({"Content-Type": "application/json"}, b"[1, 2]", 400, "bad_request"),
                 ({"Content-Type": "application/json"}, b'{"n": ' + b"9" * 5000 + b"}", 400, "bad_request"),
                 ({"Content-Type": "application/json"}, b"[" * 100_000, 400, "bad_request"))
        for headers, body, status, code in cases:
            with self.subTest(headers=headers, body=(body or b"")[:12]):
                got, _, reply = self.request("POST", "/api/preview", body, {**token, **headers})
                self.assertEqual((got, reply["code"]), (status, code))

    def test_huge_numbers_are_a_session_error(self):
        sid = self.catalog["targets"][0]["slots"][0]["id"]
        body = json.dumps({"session": {**self.session(), "values": {sid: 0}}}).encode()
        body = body.replace(b": 0}", b": " + b"7" * 400 + b"}")
        status, reply = self.post(body)
        self.assertEqual((status, reply["code"]), (400, "bad_session"))

    def test_catalog_reports_commit_and_composites(self):
        paths = [p for p in catalog().inputs if p.startswith("beadjoint/")]
        self.assertEqual(self.catalog["commit"], source_commit(ROOT, paths))
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
        # The worker cached the unedited glyphs, authenticated by a secret that stays in memory.
        secret = self.server.worker_env[CACHE_SECRET_ENV]
        self.assertRegex(secret, "^[0-9a-f]{64}$")
        files = list(Path(self.server.glyph_cache).iterdir())
        self.assertEqual([f.name for f in files], ["finished-v2.bin"])
        for f in files:
            data = f.read_bytes()
            self.assertNotIn(secret.encode(), data)
            self.assertNotIn(bytes.fromhex(secret), data)

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


class ServerLimits(unittest.TestCase):
    def test_changed_files_block_cached_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_sources(root, catalog().inputs)
            with serving(TunerServer(0, root=root)) as server:
                self.assertIsNone(server.commit, "not a Git checkout")
                token = http_request(server.server_port, "GET", "/api/catalog")[2]["token"]
                payload = json.dumps({"session": new_session(), "family": "P", "char": "a", "text": "a"}).encode()
                headers = {"Content-Type": "application/json", "X-Tuner-Token": token}
                verify_py = root / "beadjoint/verify.py"
                original = verify_py.read_bytes()

                def post():
                    status, _, body = http_request(server.server_port, "POST", "/api/preview", payload, headers)
                    return status, body

                done = subprocess.CompletedProcess([], 0, json.dumps({"checks": {"ok": True}}), "")
                with mock.patch("tuner.serve.subprocess.run", return_value=done) as worker:
                    self.assertEqual(post(), (200, {"checks": {"ok": True}}))
                    verify_py.write_bytes(original.replace(b"LINE_MIN = 1.98", b"LINE_MIN = 2.5"))
                    status, body = post()
                    self.assertEqual((status, body["code"]), (400, "sources_changed"))
                    self.assertIn("beadjoint/verify.py", body["error"])
                    verify_py.write_bytes(original)
                    self.assertEqual(post(), (200, {"checks": {"ok": True}}))
                    self.assertEqual(worker.call_count, 1)

                def change_during_run(*args, **kwargs):
                    verify_py.write_bytes(original + b"\n")
                    return done

                payload = payload.replace(b'"char": "a"', b'"char": "b"')
                with mock.patch("tuner.serve.subprocess.run", side_effect=change_during_run):
                    self.assertEqual(post()[1]["code"], "sources_changed")
                verify_py.write_bytes(original)
                with mock.patch("tuner.serve.subprocess.run", return_value=done) as worker:
                    self.assertEqual(post()[0], 200)
                    self.assertEqual(worker.call_count, 1, "a result read during a change was not kept")

    def test_connections_over_the_cap_are_refused_at_once(self):
        with serving(TunerServer(0, max_connections=2)) as server:
            port = server.server_port
            idle = [socket.create_connection(("127.0.0.1", port), timeout=10) for _ in range(2)]
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=10) as extra:
                    reply = b""
                    while chunk := extra.recv(4096):
                        reply += chunk
                head, _, body = reply.partition(b"\r\n\r\n")
                self.assertTrue(head.startswith(b"HTTP/1.0 503 "), head)
                self.assertEqual(json.loads(body)["code"], "too_many_connections")
            finally:
                for s in idle:
                    s.close()
            deadline = time.monotonic() + 10
            while True:         # the idle connections' threads notice the close and free their slots
                try:
                    status = http_request(port, "GET", "/api/catalog")[0]
                except (ConnectionError, http.client.HTTPException):
                    status = None
                if status == 200 or time.monotonic() > deadline:
                    break
                time.sleep(0.05)
            self.assertEqual(status, 200)


class Startup(unittest.TestCase):
    def test_port_in_use_is_one_line(self):
        # On Windows this needs SO_EXCLUSIVEADDRUSE: with SO_REUSEADDR the bind fails with WSAEACCES.
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen()
            port = busy.getsockname()[1]
            with mock.patch("tuner.serve.remove_stale_caches"), self.assertRaises(SystemExit) as caught:
                serve.main(["--port", str(port), "--no-browser"])
        message = str(caught.exception.code)
        self.assertIn(f"port {port} is already in use", message)
        self.assertIn("--port", message)
        self.assertNotIn("\n", message)

    def test_permission_error_suggests_another_port(self):
        denied = PermissionError(errno.EACCES, "Permission denied")
        for windows, port, reason in ((False, 80, "Choose a port from 1024 to 65535"), (True, 80, "excludedportrange"),
                                      (True, 8766, "excludedportrange")):
            message = serve.bind_error(denied, port, windows=windows)
            with self.subTest(windows=windows, port=port):
                self.assertIn(reason, message)
                self.assertIn("--port 8767", message)
                self.assertNotIn("\n", message)

    def test_stale_caches_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            old = time.time() - 2 * serve.STALE_CACHE_AGE

            def make(name, when=old):
                path = Path(directory, name)
                path.mkdir()
                (path / "finished-v2.bin").write_bytes(b"x")
                os.utime(path, (when, when))
                return path

            finished = subprocess.Popen([sys.executable, "-c", "pass"])
            finished.wait(timeout=CHILD_TIMEOUT)
            make("fillaprint-tuner-legacy1")                           # no process id, a day old: removed
            make(f"fillaprint-tuner-{finished.pid}-x")                 # its server has exited: removed
            make("fillaprint-tuner-recent", time.time())               # in use recently: kept
            make(f"fillaprint-tuner-{os.getpid()}-y")                  # its server is running: kept
            make("unrelated-old-dir")
            elsewhere = make("elsewhere")
            link = Path(directory, "fillaprint-tuner-link")
            with contextlib.suppress(OSError, NotImplementedError):
                link.symlink_to(elsewhere, target_is_directory=True)   # never followed
            removed = serve.remove_stale_caches(directory)
            expected = {"fillaprint-tuner-legacy1"} | ({f"fillaprint-tuner-{finished.pid}-x"} if os.name == "posix" else set())
            self.assertEqual(set(removed), expected)
            self.assertEqual({p.name for p in Path(directory).iterdir()} & expected, set())
            self.assertTrue((elsewhere / "finished-v2.bin").exists())

    @unittest.skipUnless(os.name == "posix", "signals")
    def test_sigterm_removes_the_cache_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.Popen([sys.executable, "-m", "tuner.serve", "--port", "0", "--no-browser"], cwd=ROOT,
                                       env={**UTF8_ENV, "TMPDIR": directory}, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, encoding="utf-8")
            try:
                self.assertIn("Fillaprint glyph tuner: http://127.0.0.1:", process.stdout.readline())
                caches = [n for n in os.listdir(directory) if n.startswith(serve.CACHE_PREFIX)]
                self.assertEqual(len(caches), 1)
                process.send_signal(signal.SIGTERM)
                self.assertEqual(process.wait(timeout=30), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
                process.stderr.close()
            self.assertEqual(os.listdir(directory), [])


if __name__ == "__main__":
    unittest.main()
