"""Frodo r4: a string whose width tells whether an app applies the fonts' kerning (Fusion check)."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
sys.path.insert(0, r"F:\code\beadjoint\review\frodo-r4")
import beadjoint.setting as st
from beadjoint.setting import ink_extent
from beadjoint.readback import FontReader
from beadjoint.specimen import draw_rows
from _nokern import nk, NoKern
from proto_setting import kerned_r4
R = r"F:\code\beadjoint\review\frodo-r4"
F = r"F:\code\beadjoint\fonts"
W = 0.32
tab = FontReader(F + r"\BeadjointTab-Regular.ttf")
prop = FontReader(F + r"\Beadjoint-Regular.ttf")
nkp = NoKern(F + r"\Beadjoint-Regular.ttf")
PROBE = ["TjTjTjTj", "1-1-1-1", "L1 L2 L3"]
for s in PROBE:
    for name, k, u in (("Tab", tab, nk), ("P", prop, nkp)):
        a, b = ink_extent(k.layout(s)), ink_extent([t for t in u.layout(s)])
        print(f"{name:3} {s!r:12} kerned {a[1]-a[0]:6.2f} w = {W*(a[1]-a[0]):5.2f} mm   no kerning {b[1]-b[0]:6.2f} w = {W*(b[1]-b[0]):5.2f} mm")
rows = [("TTF with kerning (GPOS or legacy kern)", [tab.layout(s) for s in PROBE]),
        ("TTF, advances only (an app that ignores kerning)", [nk.layout(s) for s in PROBE])]
draw_rows(rows, scale=6, path=R + r"\fusion_probe.png")
# WORD 6.0 check on caps/figure labels at print size
Q = ["L1 L2 L3 N PE", "+5V GND", 'G1/4" BSPP', "M3 x 8 SHCS", '1-1/8" - 1-13/32" dep.', "Zip ties 200 mm"]
rows = []
for word in (5.5, 6.0):
    st.WORD = word
    rows.append((f"WORD {word}", [kerned_r4(s) for s in Q]))
st.WORD = 5.5
draw_rows(rows, scale=2.6, path=R + r"\word60_small.png")
draw_rows(rows, scale=6, path=R + r"\word60_big.png")
print("ok")
