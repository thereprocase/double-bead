import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from itertools import combinations
from beadjoint.geom import finish
from beadjoint.glyphs import pieces
from beadjoint.charset import full_p
import proto_glyphs as pg
P = full_p()
scope = ("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿×÷–—‘’‚“”„†‡•…‰‹›⁄€™′″−")
def mind(g):
    ps = pieces(g)
    return min((a.distance(b) for a, b in combinations(ps, 2)), default=None)
print("current glyphs with separate pieces closer than 2.0w:")
for c in scope:
    d = mind(P[c].geom)
    if d is not None and d < 1.999:
        print(f"  {c} U+{ord(c):04X} min piece gap {d:.2f}")
print("proposed:")
for c, g in pg.proposals_all().items():
    d = mind(finish(g))
    if d is not None:
        print(f"  {c} {d:.2f}")
