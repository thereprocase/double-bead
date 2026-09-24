import sys, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
import numpy as np
from beadjoint.charset import full_mixed
from beadjoint.setting import _profile, off, BAND_FIG, BAND_X
G = full_mixed()
scope = ("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿×÷–—‘’‚“”„†‡•…‰‹›⁄€™′″−0123456789"
         + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
def shared(a, b):
    band = BAND_FIG if (a.tall or b.tall) else BAND_X
    _, ra = _profile(a, band); lb, _ = _profile(b, band)
    return int((~np.isnan(ra) & ~np.isnan(lb)).sum())
t0 = time.time()
zero = []
for ca in scope:
    for cb in scope:
        n = shared(G[ca], G[cb])
        if n == 0:
            zero.append(ca + cb)
print(len(zero), "pairs share no scanline:")
print(" ".join(zero))
# overlap for a sample of those plus legit kerning pairs
sample = [p for p in zero if any(c in p for c in "-.,_*'\"°+=~·•×’”")][:80]
legit = ["r.", "T.", "7.", "Te", "To", "Ty", "L'", "LT", "f.", "y.", "P.", "F.", "r,", "Y.", "V.", "\".", "'s", "L’", "y,", "7,"]
print("\npair  bbox-overlap(w)  [>0 means B's ink box starts left of A's right edge]")
for p in legit + sample:
    a, b = G[p[0]], G[p[1]]
    dx = off(a, b)
    print(f"{p!r:8} {a.maxx - (dx + b.minx):6.2f}  shared={shared(a, b)}")
print("secs", round(time.time() - t0, 1))
