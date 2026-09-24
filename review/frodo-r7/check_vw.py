import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_p
from beadjoint.setting import kerned, off
p = full_p()
v, w = p["v"], p["w"]
print("v bounds", v.geom.bounds, "width", v.width)
print("w bounds", w.geom.bounds, "width", w.width)
print("off(v, v)", off(v, v))
line = kerned("vv")
print("vv placed x:", [x for _, _, x in line])
print("vv ink extent", min(g.bounds[0] for _,g,_ in line), max(g.bounds[2] for _,g,_ in line))
