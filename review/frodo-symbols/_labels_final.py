import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.setting import mixed
import proto_glyphs as pg
import proto_setting as ps
from _ctx import with_, render
from beadjoint.specimen import draw_rows
R = str(Path(__file__).resolve().parents[2] / "review/frodo-symbols")
G = with_(pg.proposals_all(), "new")
lines = ["1/4\" Jt. 1/2\"-5/8\" dep. M6 x 1.0 45°", "±0.1 mm Ø12 24V DC #3 PH BIN 12-A", "¼\" ½\" ¾\" 45°-90° -.5 ±.005 Jt.*",
         "‘Jt.’ “1/2 in” it’s 50% • item", "fox jumps, les jattes; the car, the bar;"]
rows = [("now", [mixed(t) for t in lines]), ("proposed glyphs + spacing", [ps.mixed_b(t, G) for t in lines])]
render(rows, fr"{R}\labels_final.png", factor=2.5)
draw_rows(rows, scale=6, path=fr"{R}\labels_final_big.png")
for t in lines:
    bad = [(a, b, round(d, 2)) for a, b, d in ps.window_gaps(ps.mixed_b(t, G)) if d < 1.98]
    if bad:
        print("GAP FAIL", t, bad)
print("done")
