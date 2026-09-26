"""Release identifiers: the single source of truth for version strings and derived names
used by the font build, the packaging tool, the tests, and the docs.

Bump VERSION, RELEASE, and BUILD_DATE together for each release, then rebuild the fonts in
the same commit (see docs/RELEASING.md). VERSION is the internal OpenType revision
("Version " + VERSION in name ID 5, and head.fontRevision); RELEASE is the public tag used
in the CHANGELOG, README, and release archive name.

Kept free of third-party imports: tools/package_release.py reads it directly, so the
website repo can run that tool with a stock Python and no fontTools/numpy/shapely install.
"""
VERSION = "0.101"
RELEASE = "0.1.1 beta"
# head.created/modified for this revision. Fixed rather than "now" so a rebuild of the same sources
# is byte-identical; SOURCE_DATE_EPOCH (reproducible-builds.org) overrides it (see fontfile.build_epoch).
BUILD_DATE = "2026-09-25T00:00:00+00:00"

# Release archive stem, e.g. "Fillaprint-0.1.1-beta": the folder inside the ZIP and its file name.
ZIP_STEM = "Fillaprint-" + RELEASE.replace(" ", "-")
