"""Build the Fillaprint release archive from the committed fonts and license.

    python tools/package_release.py [--out DIR]      -> DIR/<ZIP_STEM>.zip, default dist/

Standard library only: this script imports beadjoint.release (which has no third-party
imports of its own) but never beadjoint.fontfile, so it runs under any stock Python 3 with
no fonttools/numpy/shapely install. That lets the website repo call it directly against a
checkout of this repo to reproduce the release archive, instead of vendoring its own
zip-building logic.

Every member is stored uncompressed (ZIP_STORED) with a fixed date, Unix file mode, and
"create system" byte, so the archive is byte-identical regardless of the Python version,
zlib build, or OS that builds it -- only a change to the font/license/INSTALL.txt bytes
changes the output. (zlib's DEFLATE output is not guaranteed stable across builds; storing
uncompressed sidesteps that entirely instead of chasing it.)

Prints "<path> <sha256>" for the archive it wrote.
"""
import argparse
import hashlib
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from beadjoint.release import BUILD_DATE, RELEASE, VERSION, ZIP_STEM  # noqa: E402

FONT_FILES = ["Fillaprint-Regular.ttf", "FillaprintTab-Regular.ttf", "FillaprintMono-Regular.ttf"]
# Fixed Unix permissions (-rw-r--r--) in the high 16 bits of external_attr, and a fixed
# create_system (3 = Unix), so the archive bytes do not depend on the platform building it:
# zipfile.ZipInfo defaults create_system to 0 on win32 and 3 elsewhere unless told otherwise.
_EXTERNAL_ATTR = 0o100644 << 16
_CREATE_SYSTEM = 3


def install_text():
    """INSTALL.txt body, bundled inside the archive. Moved here from the website's sync
    script so the archive is self-describing; wording is unchanged, versions come from
    beadjoint/release.py."""
    return f"""Fillaprint v{RELEASE} — by Repro
Internal font version: {VERSION}

Fine-tuning for release. A future Nerd Fonts launch is a target;
this is not an official Nerd Fonts release.

Install the three TTF files with your operating system's font installer.
Restart your CAD/design app if needed. Select Fillaprint, Fillaprint Tab (equal-width digits), or Fillaprint Mono.

At extrusion line width w, capital height = 14w; em size = 20w.
For w = 0.42 mm, start with 5.88 mm capitals (Fusion Height) / 8.40 mm em.
Inspect the sliced preview before printing.

Free for personal and commercial use under SIL OFL 1.1. Retain the license
and copyright notices when distributing fonts. Modified font versions must
use different names unless permission is granted. See OFL.txt for full terms.

https://thereprocase.github.io/fillaprint/
https://github.com/thereprocase/double-bead
"""


def _date_time():
    """ZipInfo date_time tuple from BUILD_DATE (no SOURCE_DATE_EPOCH here: that only affects
    the font timestamps via beadjoint.fontfile.build_epoch, which this script does not import)."""
    dt = datetime.fromisoformat(BUILD_DATE)
    return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def members():
    """{member name -> bytes}, keys without the ZIP_STEM/ folder prefix."""
    fonts_dir = ROOT / "fonts"
    files = {name: (fonts_dir / name).read_bytes() for name in FONT_FILES}
    files["OFL.txt"] = (ROOT / "OFL.txt").read_bytes()
    files["INSTALL.txt"] = install_text().encode("utf-8")
    return files


def build(out_dir):
    """Write <out_dir>/<ZIP_STEM>.zip and return (path, sha256_hex)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"{ZIP_STEM}.zip"
    date_time = _date_time()
    data = members()
    with zipfile.ZipFile(archive_path, "w") as zf:
        for name in sorted(data):
            info = zipfile.ZipInfo(f"{ZIP_STEM}/{name}", date_time)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = _EXTERNAL_ATTR
            info.create_system = _CREATE_SYSTEM
            zf.writestr(info, data[name])
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return archive_path, digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "dist"), help="output directory (default: dist/)")
    args = parser.parse_args(argv)
    path, digest = build(args.out)
    print(f"{path} {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
