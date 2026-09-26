"""Where the tests run, and what CI tells them through the environment (docs/DEVELOPMENT.md, "Platforms"
and "Continuous integration"). Imported by test_beadjoint and test_release; it holds no tests itself."""
import os
import platform
import sys
import unittest

# The release fonts are built on Linux x86-64 with glibc. Their glyph geometry was found identical on glibc
# 2.39 (x86-64 and aarch64, CI's ubuntu-24.04 images) and glibc 2.44 (x86-64). Every Linux with glibc counts
# as the reference, so an unverified glibc, architecture or CPU gets the exact tolerances: if its geometry
# differs, the tests fail rather than quietly loosening.
REFERENCE = sys.platform == "linux" and platform.libc_ver()[0] == "glibc"

# CI sets this on its Linux jobs: a runner image that stops being the reference must fail, not fall back to
# another platform's slack. test_beadjoint.CISwitches checks it.
REQUIRE_REFERENCE = os.environ.get("FILLAPRINT_REQUIRE_REFERENCE") == "1"

# CI sets this on pull requests only. Contributions are source-only (docs/TUNER.md), so a pull request's
# committed fonts may predate its sources. The tests that compare the committed fonts with the sources, or
# with constants taken from them, then skip; CI's build job runs them on fonts built from the pull request's
# sources instead. Unset (locally, and on main), none of them skips. test_beadjoint.CISwitches fails a run
# that sets it on any GitHub event but a pull request.
STALE_FONTS_OK = os.environ.get("FILLAPRINT_COMMITTED_FONTS_MAY_BE_STALE") == "1"
compares_fonts_with_sources = unittest.skipIf(
    STALE_FONTS_OK, "compares the committed fonts with the sources, which FILLAPRINT_COMMITTED_FONTS_MAY_BE_STALE=1 "
                    "says may be newer; CI's build job runs it on fonts built from these sources")
