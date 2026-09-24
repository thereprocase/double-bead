"""Monospace: ĺ is dropped (compose forces the acute to x = 1, off the mono l's stem at 4.5, so the
glyph is 10.1w and fails MONO_MAX); ď ť (apostrophe form) do not fit either. Prototype: ĺ with the
acute on the stem; ď ť with a real caron centred on the letter (fits the 10w limit)."""
from _lib import *
from beadjoint.charset import full_m, MONO_MAX
M = full_m()
out = {}
ml = M["l"].geom
out["ĺ M"] = finish(ml | place_above(SHAPES["acute"], 4.5, marks.ABOVE_HIGH))
for c in "dt":
    g = M[c].geom
    x0, _, x1, _ = g.bounds
    out[c + "caron M"] = finish(g | place_above(SHAPES["caron"], (x0 + x1) / 2, marks.ABOVE_HIGH))
for k, g in out.items():
    audit(k, g)
    print("   width", round(g.bounds[2] - g.bounds[0], 2), "fits" if g.bounds[2] - g.bounds[0] <= MONO_MAX else "TOO WIDE")
ref = {"l M": M["l"].geom, "Ľ M": M["Ľ"].geom, "č M": M["č"].geom, "Ť M": M["Ť"].geom}
sheet({**out, **ref}, "mono.png", cols=7, scale=6, cell=(16, 32))
