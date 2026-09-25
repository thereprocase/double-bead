import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p, raw_p
from beadjoint.glyphs import Glyph
from beadjoint.sheet import grid
import acute
P, R = full_p(), raw_p()
C = sys.argv[1]
d = {}
for c in C:
    d[c + " cur"] = P[c]
    d[c + " acute"] = Glyph(c, "x", acute.finish_acute(R[c]))
grid(d, str(Path(__file__).resolve().parents[2] / "review/frodo-r3") + "/" + sys.argv[2], cols=8, scale=12, cell=(14, 26))
