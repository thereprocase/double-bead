import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.setting import mixed
import proto_setting as ps
from _ctx import render
R = r"F:\code\beadjoint\review\frodo-symbols"
lines = ["The quick brown fox jumps over the lazy dog.", "les jattes de kiwis, jeden Tag", "1/4\" Jt. 1/2\"-5/8\" dep. 45°-90°",
         "M6 x 1.0 ±.005 -.5 mm #3 PH a_b \"stop.\"", "Ty. r. P. 7. It's 12:30 (a) [1]"]
rows = [("now", [mixed(t) for t in lines])]
for wm in (3.0, 3.5, 4.0):
    ps.WORD_MIN = wm
    ls = [ps.mixed2(t) for t in lines]
    rows.append((f"proposed, WORD_MIN {wm}", ls))
    bad = [(a, b, round(d, 2)) for ln in ls for a, b, d in ps.window_gaps(ln) if d < 1.98]
    print("WORD_MIN", wm, "window gaps < 1.98:", bad)
render(rows, fr"{R}\spacing_ctx.png", factor=2.5)
