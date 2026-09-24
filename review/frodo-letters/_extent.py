from _lib import *
ys = sorted(((g.bounds[1], g.bounds[3], c) for c, g in P.items()), key=lambda t: t[0])
print("highest ink:", [(c, round(a, 2)) for a, b, c in ys[:8]])
lo = sorted(((g.bounds[3], c) for c, g in P.items()), reverse=True)
print("lowest ink:", [(c, round(b, 2)) for b, c in lo[:8]])
top, bot = ys[0][0], lo[0][0]
print(f"font units: yMax {(10 - top) * 50:.0f}  yMin {(10 - bot) * 50:.0f}  (usWinAscent/Descent now 700/200)")
print("count above y=-4:", sum(1 for a, b, c in ys if a < -4.2), " below y=14:", sum(1 for b, c in lo if b > 14.2))
# line collision at the 20w pitch: cap accent vs descender of the line above
print("cap accents above -4:", "".join(c for a, b, c in ys if a < -4.2 and c.isupper()))
