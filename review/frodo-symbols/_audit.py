import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_p, full_mixed
from beadjoint.verify import check_glyph
from beadjoint.sheet import grid
from beadjoint.glyphs import pieces
R = r"F:\code\beadjoint\review\frodo-symbols"
P = full_p()
scope = ("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" + "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿×÷"
         + "–—‘’‚“”„†‡•…‰‹›⁄€™′″−" + "0123456789")
for c in scope:
    g = P[c]
    r = check_glyph(g.geom)
    b = g.bounds
    print(f"{c} U+{ord(c):04X} x[{b[0]:5.2f},{b[2]:5.2f}] y[{b[1]:5.2f},{b[3]:5.2f}] w={b[2]-b[0]:5.2f} ymid={(b[1]+b[3])/2:5.2f} "
          f"T={r['thickness']:.2f}@{r['at']} pcs={len(pieces(g.geom))} tall={g.tall} thin={r['thin']} isl={r['islands']}")
half = (len(scope) + 1) // 2
grid({c: P[c] for c in scope[:half]}, fr"{R}\scope_a.png", cols=12, scale=10, cell=(18, 24))
grid({c: P[c] for c in scope[half:]}, fr"{R}\scope_b.png", cols=12, scale=10, cell=(18, 24))
