import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.setting import mixed, kerned
from beadjoint.charset import full_mixed
import proto_setting as ps
from _ctx import render
R = r"F:\code\beadjoint\review\frodo-symbols"
G = full_mixed()
lines = ["The quick brown fox jumps over the lazy dog.", "les jattes de kiwis, jeden Tag, ąę jeż",
         "1/4\" Jt. 1/2\"-5/8\" dep. 45°-90°", "M6 x 1.0 ±.005 -.5 mm #3 PH a_b \"stop.\"",
         "Ty. r. P. 7. It's 12:30 (a) [1] BIN 12-A"]
print("glyphs whose word-space edge moves under rule B (band [-4,10] vs bbox):")
moved = []
for c, g in G.items():
    l, r = ps.band_x(g)
    if abs(l - g.minx) > 0.05 or abs(r - g.maxx) > 0.05:
        moved.append(f"{c}(L{l - g.minx:+.1f} R{r - g.maxx:+.1f})")
print(" ".join(moved))
for a in ["n j", "x j", "e T", "n 1", "x 1", "M 6"]:
    now, new = mixed(a), ps.mixed_b(a)
    print(f"  '{a}': first-ink gap now {now[1][1].bounds[0] - now[0][1].bounds[2]:.2f}  rule B {new[1][1].bounds[0] - new[0][1].bounds[2]:.2f}")
bad = [(a, b, round(d, 2)) for t in lines for a, b, d in ps.window_gaps(ps.mixed_b(t)) if d < 1.98]
print("rule B window gaps < 1.98:", bad)
bad = [(a, b, round(d, 2)) for t in lines for a, b, d in ps.window_gaps(ps.kerned_b(t)) if d < 1.98]
print("rule B kerned window gaps < 1.98:", bad)
render([("now (setting.mixed)", [mixed(t) for t in lines]),
        ("rule B: stack guard + WORD on band [-4,10] from whole previous word + figure run ink at the edge",
         [ps.mixed_b(t) for t in lines])], fr"{R}\spacing_ctx.png", factor=2.5)
