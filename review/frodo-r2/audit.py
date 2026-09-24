"""Audit every composite and special letter: thin ink, islands, piece gaps, bounds; mark sizes."""
from _lib import *

P = full_p()
print("--- mark shapes (raw, unfinished): width x height")
for n, m in SHAPES.items():
    x0, y0, x1, y1 = m.bounds
    print(f"{n:12s} {x1 - x0:.2f} x {y1 - y0:.2f}")

print("--- composites")
comp = [c for c in CHARS if marks.decompose(c)]
fails = []
tops, bots = {}, {}
for c in comp:
    f = P[c].geom
    r = audit(c, f)
    tops[c], bots[c] = f.bounds[1], f.bounds[3]
print("composites:", len(comp))
print("--- specials")
for c in "đĐÐðħĦŧŦłŁøØæÆœŒŋŊĸıȷĳĲŉſþÞŀĿ":
    audit(c, P[c].geom)
print("--- extremes")
print("highest:", sorted(tops.items(), key=lambda kv: kv[1])[:8])
print("lowest:", sorted(bots.items(), key=lambda kv: -kv[1])[:8])
