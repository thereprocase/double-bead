import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_p, MONO_MAX
p = full_p()
for c in ["M", "W"]:
    g = p[c]
    print(c, "bounds", g.bounds, "width", g.width, "over", g.width - MONO_MAX)
