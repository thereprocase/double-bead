"""Line pitch vs accents: the smallest pitch at which glyph b on the next line stays 2w from glyph a
on the line above, whatever their horizontal offset. The fonts (and README) say 20w."""
from _lib import *
import numpy as np

P = full_p()


def worst(a, b, pitch):
    ga, gb = P[a].geom, shift(P[b].geom, 0, pitch)
    x0 = ga.bounds[0] - gb.bounds[2] - 1
    x1 = ga.bounds[2] - gb.bounds[0] + 1
    return min(ga.distance(shift(gb, dx)) for dx in np.arange(x0, x1, 0.25))


def need(a, b):
    lo, hi = 10.0, 40.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if worst(a, b, mid) >= 2.0:
            hi = mid
        else:
            lo = mid
    return hi


pairs = [("g", "H"), ("g", "("), ("g", "["), ("g", "á"), ("p", "Á"), ("y", "Ě"), ("g", "Å"), ("q", "Ů"),
         ("ç", "Á"), ("ș", "Á"), ("ģ", "Ă"), ("Ņ", "Å"), ("H", "Á"), ("a", "Ä"), ("n", "É")]
for a, b in pairs:
    print(f"{a} over {b}: at 20w pitch min distance {worst(a, b, 20):.2f}w; needs pitch {need(a, b):.2f}w")
