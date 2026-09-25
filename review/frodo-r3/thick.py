import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p, raw_p
from beadjoint.geom import soft, finish
from beadjoint.verify import check_glyph
P = full_p(); R = raw_p()
for c in sys.argv[1]:
    r = check_glyph(P[c].geom)
    r2 = check_glyph(soft(R[c]))
    print(c, "finished", r["thickness"], r["at"], "| soft-only", r2["thickness"], r2["at"], "area", round(P[c].geom.area, 2), round(soft(R[c]).area, 2))
