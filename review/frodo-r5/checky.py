import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.latin import capitals
from beadjoint.geom import finish
from beadjoint.verify import check_glyph
c = capitals()
for k in ("Y", "K", "N", "M", "X"):
    r = check_glyph(finish(c[k]))
    print(k, r["thickness"], r["at"])
