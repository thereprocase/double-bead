import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_p
p = full_p()
for c in "0ODQ":
    g = p[c]
    print(c, g.geom.bounds, "area", round(g.geom.area, 3))
