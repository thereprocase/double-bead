import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from functools import lru_cache
from beadjoint.charset import full_mixed
import proto_setting as ps
from _ctx import render
R = str(Path(__file__).resolve().parents[2] / "review/frodo-symbols")
G = full_mixed()
text = ["jar, jig; far. r: P. F. L' T. 7, y, Ty. \"r\"", "the car, the bar; P.S. Jt. dep. Fig. 7."]
rows = [("now + stack guard", [ps.mixed2(t) for t in text])]
base = ps.off2.__wrapped__
for cap in (1.5, 1.0):
    @lru_cache(maxsize=None)
    def capped(a, b, cap=cap):
        return max(base(a, b), a.maxx - b.minx - cap)
    ps.off2 = capped
    rows.append((f"tuck capped at {cap}w bbox overlap", [ps.mixed2(t) for t in text]))
render(rows, fr"{R}\tuck.png", factor=2.0)
ps.off2 = base
big = []
for a in "rPFLTVY7fy":
    for b in ".,:;'’\"":
        if a + b in ("TV",):
            continue
        ga, gb = G[a], G[b]
        ov = ga.maxx - (ps.off2(ga, gb) + gb.minx)
        if ov > 1.5:
            big.append(f"{a}{b}:{ov:.1f}")
print("pairs tucking more than 1.5w:", " ".join(big))
