"""Release-tooling tests: version strings stay in sync with beadjoint/release.py, and
tools/package_release.py produces a byte-reproducible archive with the expected contents.

    python -m unittest discover -s tests      (from the repo root)

These tests read committed files (fonts, docs, scripts) and run the packaging tool; they do
not rebuild the fonts (see build.py / docs/DEVELOPMENT.md for the full pinned rebuild).
"""
import hashlib
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from beadjoint.release import BUILD_DATE, RELEASE, VERSION, ZIP_STEM  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
import package_release  # noqa: E402

FONT_FILES = ["Fillaprint-Regular.ttf", "FillaprintTab-Regular.ttf", "FillaprintMono-Regular.ttf"]
# "## [Unreleased — ]v<release> (OpenType <version>)" -- see the comment at the top of CHANGELOG.md.
CHANGELOG_HEADING = re.compile(r"^## (?:.*— )?v(?P<release>[0-9][0-9.]* beta) \(OpenType (?P<version>[0-9.]+)\)$")


class FontVersions(unittest.TestCase):
    """Every committed TTF must carry the current VERSION in its name table."""

    def test_name_id_5(self):
        for name in FONT_FILES:
            font = TTFont(str(ROOT / "fonts" / name))
            self.assertEqual(font["name"].getDebugName(5), f"Version {VERSION}", name)


class ChangelogAndReadme(unittest.TestCase):
    def test_changelog_top_entry_matches_release(self):
        lines = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
        headings = [line for line in lines if line.startswith("## ")]
        self.assertTrue(headings, "CHANGELOG.md has no release headings")
        m = CHANGELOG_HEADING.match(headings[0])
        self.assertIsNotNone(m, f"unparseable heading: {headings[0]!r}")
        self.assertEqual(m.group("release"), RELEASE)
        self.assertEqual(m.group("version"), VERSION)

    def test_readme_mentions_current_release(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"v{RELEASE}", text)
        self.assertIn(f"{ZIP_STEM}.zip", text)


class InstallScriptVersion(unittest.TestCase):
    """tools/install_fonts.ps1 must not fall back to a version that no longer matches the
    fonts it installs: either it has no stale hardcoded default (it reads release.py/the
    font at runtime), or any literal default it does carry matches VERSION."""

    def test_no_stale_default(self):
        text = (ROOT / "tools" / "install_fonts.ps1").read_text(encoding="utf-8")
        default = re.search(r'\[string\]\$Version\s*=\s*"([^"]+)"', text)
        if default:
            self.assertEqual(default.group(1), VERSION, "hardcoded -Version default is stale")
        else:
            # No hardcoded default: it must read the version dynamically instead of assuming one.
            self.assertRegex(text, r"release\.py", "no hardcoded default and no dynamic version read")


class PackageRelease(unittest.TestCase):
    def _expected_members(self):
        names = FONT_FILES + ["OFL.txt", "INSTALL.txt"]
        return sorted(f"{ZIP_STEM}/{n}" for n in names)

    def test_reproducible_bytes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            path_a, digest_a = package_release.build(a)
            path_b, digest_b = package_release.build(b)
            self.assertEqual(digest_a, digest_b)
            self.assertEqual(path_a.read_bytes(), path_b.read_bytes())
            self.assertEqual(digest_a, hashlib.sha256(path_a.read_bytes()).hexdigest())

    def test_member_list_and_storage(self):
        with tempfile.TemporaryDirectory() as out:
            path, _ = package_release.build(out)
            with zipfile.ZipFile(path) as zf:
                self.assertEqual(sorted(zf.namelist()), self._expected_members())
                for info in zf.infolist():
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED, info.filename)
                    self.assertEqual(info.create_system, 3, info.filename)
                fonts = zf.read(f"{ZIP_STEM}/Fillaprint-Regular.ttf")
                self.assertEqual(fonts, (ROOT / "fonts" / "Fillaprint-Regular.ttf").read_bytes())
                install = zf.read(f"{ZIP_STEM}/INSTALL.txt").decode("utf-8")
                self.assertIn(RELEASE, install)
                self.assertIn(VERSION, install)

    def test_cli_prints_path_and_sha256(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "package_release.py"), "--out", out],
                capture_output=True, text=True, check=True, cwd=str(ROOT))
            self.assertRegex(result.stdout.strip(), r"^\S+\.zip [0-9a-f]{64}$")

    def test_zip_stem_matches_release(self):
        self.assertEqual(ZIP_STEM, "Fillaprint-" + RELEASE.replace(" ", "-"))
        self.assertTrue(BUILD_DATE)  # sanity: package_release._date_time() must be able to parse it
        package_release._date_time()


if __name__ == "__main__":
    unittest.main()
