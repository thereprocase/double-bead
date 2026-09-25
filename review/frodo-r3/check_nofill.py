import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.verify import check_glyph
import proto_nofill as pn
for k, c in enumerate(pn.CHARS):
    a = check_glyph(pn.GLYPHS[2 * k][1]); b = check_glyph(pn.GLYPHS[2 * k + 1][1])
    print(c, "cur", a["thickness"], "nofill", b["thickness"], "thin", b["thin"], "isl", b["islands"],
          "area", round(pn.GLYPHS[2 * k][1].area, 2), round(pn.GLYPHS[2 * k + 1][1].area, 2))
