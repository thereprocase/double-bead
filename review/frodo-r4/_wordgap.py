"""Frodo r4: gap across a space, engine vs Tab TTF, for every printable ASCII pair and overhang contexts."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
import numpy as np
from beadjoint.setting import mixed
from beadjoint.readback import FontReader
tab = FontReader(r"F:\code\beadjoint\fonts\BeadjointTab-Regular.ttf")
A = [chr(c) for c in range(0x21, 0x7F)]


def across(line, k):
    """True distance from glyph k (first of word 2) to the nearest glyph of word 1 (all before k)."""
    return min(line[k][1].distance(g) for _, g, _ in line[:k])


rows = []
for a in A:
    for b in A:
        s = a + " " + b
        e, t = mixed(s), tab.layout(s)
        rows.append((across(t, 1) - across(e, 1), s, across(e, 1), across(t, 1)))
d = np.array([r[0] for r in rows])
print(f"ASCII 'a b': ttf - engine true gap: mean {d.mean():+.2f} min {d.min():+.2f} max {d.max():+.2f}; "
      f"|diff| > 0.5 in {(abs(d) > 0.5).sum()} of {len(d)}")
print("TTF min gap across a space:", round(min(r[3] for r in rows), 2), "engine min:", round(min(r[2] for r in rows), 2))
rows.sort()
print("TTF tighter than engine:", [(r[1], round(r[2], 2), round(r[3], 2)) for r in rows[:8]])
print("TTF looser than engine:", [(r[1], round(r[2], 2), round(r[3], 2)) for r in rows[-8:]])
ctx = []
for w1 in ["T.", "f,", "r.", "7.", "P.", "F,", "Y.", "V,", "Tj", "f)", "y.", "L'", "1\"", "4\"", 'r"', "*,"]:
    for b in "AJTjy14(\"'":
        s = w1 + " " + b
        e, t = mixed(s), tab.layout(s)
        ctx.append((across(t, 2) - across(e, 2), s, across(e, 2), across(t, 2)))
ctx.sort()
print("overhang contexts, TTF tighter:", [(r[1], round(r[2], 2), round(r[3], 2)) for r in ctx[:8]])
print("min TTF gap in contexts:", round(min(r[3] for r in ctx), 2))
