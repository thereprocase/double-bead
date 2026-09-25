"""License metadata shared by font builds and distribution tools."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPYRIGHT = "Copyright 2026 Repro (https://github.com/thereprocase)"
LICENSE_URL = "https://openfontlicense.org/"
LICENSE_TEXT = (ROOT / "OFL.txt").read_text(encoding="utf-8").strip()


def apply_license(font):
    """Keep the license with a standalone TTF and permit installable embedding."""
    values = {0: COPYRIGHT, 9: "Repro", 12: "https://github.com/thereprocase/double-bead",
              13: LICENSE_TEXT, 14: LICENSE_URL}
    for name_id, value in values.items():
        font["name"].removeNames(nameID=name_id)
        font["name"].setName(value, name_id, 3, 1, 0x409)
    font["OS/2"].fsType = 0
