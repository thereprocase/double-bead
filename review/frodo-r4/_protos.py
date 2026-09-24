"""Frodo r4: prototype images (P vs Tab on labels with 1s; runs of spaces; tracking and word space)."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
sys.path.insert(0, r"F:\code\beadjoint\review\frodo-r4")
import beadjoint.setting as st
from beadjoint.setting import mixed, kerned, ink_extent
from beadjoint.readback import FontReader
from beadjoint.specimen import draw_rows
from beadjoint.verify import line_gaps
from proto_setting import kerned_r4, mixed_r4

R = r"F:\code\beadjoint\review\frodo-r4"
F = r"F:\code\beadjoint\fonts"
tab = FontReader(F + r"\BeadjointTab-Regular.ttf")
prop = FontReader(F + r"\Beadjoint-Regular.ttf")


def check(lines, tag):
    bad = [(a, b, round(d, 3)) for ln in lines for a, b, d in line_gaps([(c, g) for c, g, _ in ln]) if d < 1.98]
    print(f"{tag}: {'window check ok' if not bad else bad}")


# 1. Q3: labels with 1 next to 4 / 7 / 1
Q3 = ["14 AWG  M14 x 1.5  17 mm", "BIN 11  11-17  #10-24", "1/4-14 NPT  T10  Ø14", "110 V  M10 x 1.25  1:1"]
sp1 = lambda s: s.replace("  ", " ")
rows = [("Beadjoint Tab (TTF): the tabular 1 leaves holes: 14, 17, 11", [tab.layout(s) for s in Q3]),
        ("Beadjoint (TTF), proportional figures", [prop.layout(s) for s in Q3])]
draw_rows(rows, scale=7, path=R + r"\q3_tab_vs_p.png")
draw_rows(rows, scale=2.6, path=R + r"\q3_tab_vs_p_small.png")
check([mixed_r4(s) for s in Q3] + [kerned_r4(s) for s in Q3], "q3 engine")

# stacked list: where Tab earns its keep
LIST = ["M3 x 6", "M3 x 10", "M3 x 12", "M3 x 14", "M3 x 16", "M3 x 17", "M3 x 20"]


def right_align(lines):
    his = [ink_extent(ln)[1] for ln in lines]
    m = max(his)
    from shapely import affinity
    return [[(c, affinity.translate(g, m - hi), x + m - hi) for c, g, x in ln] for ln, hi in zip(lines, his)]


rows = [("stacked, right-aligned: Tab (9w cells)", right_align([mixed(s) for s in LIST])),
        ("stacked, right-aligned: proportional", right_align([kerned(s) for s in LIST]))]
draw_rows(rows, scale=5, path=R + r"\q3_stacked.png")

# 2. runs of spaces: the review's own label lines use three spaces between labels
LINES = ['1/4" Jt.   1/2" - 5/8" dep.   5/16" Jt.', "M3 x 8 SHCS   M4 x 12 BHCS", "IN / OUT   OFF - ON   HOT",
         "12\u00a0mm  (no-break space)"]
rows = [("engine now: runs of spaces collapse to one word space (NBSP line: KeyError, left out)", [mixed(s) for s in LINES[:3]]),
        ("engine proposed (mixed_r4): n spaces = WORD + (n-1) x space advance; NBSP = space", [mixed_r4(s) for s in LINES]),
        ("BeadjointTab-Regular.ttf", [[t for t in tab.layout(s) if not t[1].is_empty] for s in LINES])]
draw_rows(rows, scale=6, path=R + r"\spaces.png")
for s in LINES:
    e, t = mixed_r4(s), [t for t in tab.layout(s) if not t[1].is_empty]
    we, wt = ink_extent(e)[1] - ink_extent(e)[0], ink_extent(t)[1] - ink_extent(t)[0]
    print(f"  {s!r:44} proposed engine {we:7.2f}  ttf {wt:7.2f}  ({wt - we:+.2f})")

# 3. Q4: tracking and word space at print size (proportional)
Q4 = ["SPARE FUSES 5A", "M3 x 8 SHCS", "WAGO 221-413", "L1 L2 L3 N PE", "Zip ties 200 mm", '1-1/8" - 1-13/32" dep.']
rows = []
for tag, word, track in (("now: WORD 5.5, no tracking", 5.5, 0.0), ("tracking +0.3 w", 5.5, 0.3),
                         ("WORD 6.5", 6.5, 0.0), ("WORD 4.5", 4.5, 0.0)):
    st.WORD = word
    st._edges.cache_clear()
    rows.append((tag, [kerned_r4(s, track=track) for s in Q4]))
st.WORD = 5.5
draw_rows(rows, scale=2.6, path=R + r"\q4_small.png")
draw_rows(rows[:2], scale=6, path=R + r"\q4_big.png")
print("ok")
