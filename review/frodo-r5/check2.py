import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")

from beadjoint.glyphs import FIGURES
from beadjoint.charset import full_p, full_mixed
from beadjoint.verify import check_glyph, line_gaps
from beadjoint.setting import kerned, mixed
from beadjoint.specimen import draw_rows

p = full_p()

print("=== figures 0-9 ===")
for c in FIGURES:
    r = check_glyph(p[c].geom)
    print(f"{c} thick={r['thickness']:.2f} thin={r['thin']} islands={r['islands']} bounds={[round(b,2) for b in p[c].bounds]}")

print()
print("=== superscripts, fractions, degree, plusminus, times, mu, percent, hash ===")
for c in ["¹", "²", "³", "¼", "½", "¾", "°", "±", "×", "µ", "%", "#"]:
    if c not in p:
        print(f"MISSING key {c!r} codepoints={[hex(ord(ch)) for ch in c]}; dict has similar: "
              + repr([k for k in p if len(k) == 1 and abs(ord(k) - ord(c)) < 3]))
        continue
    g = p[c]
    r = check_glyph(g.geom)
    print(f"{c} thick={r['thickness']:.2f} thin={r['thin']} islands={r['islands']} bounds={[round(b,2) for b in g.bounds]}")

print()
print("=== '12:30' kerned (set P) ===")
line = kerned("12:30")
for ch, geom, x in line:
    print(f"{ch}: x={x:.2f} bounds={[round(b,2) for b in geom.bounds]}")
gaps = line_gaps([(c, g) for c, g, x in line])
print("gaps:", [(a, b, round(d, 3)) for a, b, d in gaps])

print()
print("=== '12:30' mixed (tabular figures) ===")
m = full_mixed()
line2 = mixed("12:30", m)
for ch, geom, x in line2:
    print(f"{ch}: x={x:.2f} bounds={[round(b,2) for b in geom.bounds]}")

draw_rows([("12:30 kerned", [line]), ("12:30 mixed", [line2])], scale=24,
          path=r"F:\code\beadjoint\review\frodo-r5\time_check.png")
print("wrote time_check.png")
