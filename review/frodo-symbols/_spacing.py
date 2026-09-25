import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_mixed
from beadjoint.setting import mixed, WORD
import proto_setting as ps
from _ctx import render
R = str(Path(__file__).resolve().parents[2] / "review/frodo-symbols")
G = full_mixed()
n = G["n"]

print("word space across ' ' : bbox ink gap now = 5.50 for every pair; proposed (bbox / first-stem):")
for a, b in ["nn", "nj", "xj", "oj", "sj", "aj", "eT", "rn", "fn", "yn", "ny", "n7", "n1", "1n", "Jn", "n'", "n(", ".n", "n/", "nV", "Tn", "L1", "on", "no"]:
    ga, gb = G[a], G[b]
    dx = ps.word_dx(ga, gb, n)
    print(f"  {a}_{b}: bbox gap {dx - ga.maxx + gb.minx:5.2f}")
# figure run after a space: current rule adds the cell padding
for a, b in ["n1", "n4", "x1", "M6"]:
    now = mixed(a + " " + b)
    new = ps.mixed2(a + " " + b)
    print(f"  mixed {a} {b}: bbox gap now {now[1][1].bounds[0] - now[0][1].bounds[2]:.2f}  proposed {new[1][1].bounds[0] - new[0][1].bounds[2]:.2f}")

lines = ["The quick brown fox jumps over the lazy dog.", "les jattes de kiwis, jeden Tag", "1/4\" Jt. 1/2\"-5/8\" dep. 45°-90°",
         "M6 x 1.0 ±.005 -.5 mm #3 PH a_b \"stop.\"", "Ty. r. P. 7. It's 12:30 (a) [1]"]
for t in lines:
    for name, fn in (("now", mixed), ("new", ps.mixed2)):
        ln = fn(t)
        bad = [(a, b, round(d, 2)) for a, b, d in ps.window_gaps(ln) if d < 1.98]
        print(f"{name}: {t!r}\n    window(3) gaps < 1.98: {bad}")
render([("now (setting.mixed)", [mixed(t) for t in lines]), ("proposed (stack guard + optical word space)", [ps.mixed2(t) for t in lines])],
       fr"{R}\spacing_ctx.png", factor=2.5)
