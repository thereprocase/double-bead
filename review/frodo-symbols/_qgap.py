import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.geom import finish
from beadjoint.latin import shift
import proto_glyphs as pg
p = pg.proposals()
for c in "’‘,":
    g = finish(p[c])
    lo, hi = 3.0, 8.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if g.distance(shift(g, mid)) < 2.0:
            lo = mid
        else:
            hi = mid
    print(c, "offset for 2.0w gap:", round(hi, 3), " bbox gap then:", round(hi - (g.bounds[2] - g.bounds[0]), 2))
