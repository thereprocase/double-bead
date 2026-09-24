import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.setting import kerned, mixed, ink_extent
from beadjoint.specimen import draw_rows
from beadjoint.verify import line_gaps
R = r"F:\code\beadjoint\review\frodo-symbols"
lines = ["!\"#$%&'()*+,-./", ":;<=>?@[\\]^_`{|}~", "a_b x_y (x) [1] {a} a|b", "‘quoted’ “quoted” „low“ it’s 5′ 6″",
         "45% 3‰ • item · x 2×3 2*3 a*b Jt.*", "fox jumps  jeden  les jattes  a j", "BIN 12-A  12:30  1:2  -5 °C  ±0.1"]
rows = [(t, [mixed(t)]) for t in lines]
draw_rows(rows, scale=6, path=fr"{R}\lines_now.png")
for t in lines:
    ln = mixed(t)
    bad = [(a, b, round(d, 2)) for a, b, d in line_gaps([(c, g) for c, g, _ in ln]) if d < 2.2]
    # horizontal overlap between neighbours (ink of b starts before ink of a ends)
    ov = []
    for (ca, ga, _), (cb, gb, _) in zip(ln, ln[1:]):
        if gb.bounds[0] < ga.bounds[2] - 0.01:
            ov.append((ca, cb, round(ga.bounds[2] - gb.bounds[0], 2)))
    print(repr(t), "\n   tight<2.2:", bad, "\n   bbox overlap:", ov)
