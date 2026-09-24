"""Prototypes: ģ comma above, round breve / ring / tilde, ŗ comma under the stem, ĸ like K,
đ ħ bars, ð with a bar. Builds composites from the finished bases exactly as charset._assemble does."""
from _lib import *
import math

P = full_p()
FIN = {c: g.geom for c, g in P.items()}
RAW = raw_p()

NEW = dict(SHAPES)
NEW["breve"] = S((0, 0, B), (0, 2.5, 2.5), (5, 2.5, 2.5), (5, 0, B))           # half circle, r = 2.5
NEW["ring"] = So((0, 0, 2), (4, 0, 2), (4, 4, 2), (0, 4, 2))                     # true circle, 6w, 2w hole
NEW["tilde"] = S((0, 2, B), (2, 0, 1.4), (4, 2, 1.4), (6, 0, B))                 # softer wave


def comp(ch, shapes=NEW, below_x=None):
    """compose() with replacement shapes, ģ fixed (cedilla on g -> turned comma above) and per-base
    comma-below x."""
    base, ms = decompose(ch)
    saved = dict(marks.SHAPES)
    marks.SHAPES.update(shapes)
    try:
        if base == "g" and ms == ["cedilla"]:
            ms = ["commabelow"]                      # ģ: U+0123 decomposes to g + cedilla (U+0327)
        g = compose(ch, base, ms, FIN)
        if below_x and base in below_x:              # rebuild with the comma under the stem
            b = FIN[base]
            g = b | place_below(marks.SHAPES["commabelow"], below_x[base])
    finally:
        marks.SHAPES.clear()
        marks.SHAPES.update(saved)
    return finish(g)


out = {}
# 1. ģ
out["ģ now"] = P["ģ"].geom
out["ģ fix"] = comp("ģ")
# 2-3. breve, ring, tilde
for c in "ăĂğĞŭŬ":
    out[c + " now"] = P[c].geom
    out[c + " rnd"] = comp(c)
for c in "åÅůŮ":
    out[c + " now"] = P[c].geom
    out[c + " rnd"] = comp(c)
for c in "ãÑõĩ":
    out[c + " now"] = P[c].geom
    out[c + " soft"] = comp(c)
# 4. ŗ under the stem
out["ŗ now"] = P["ŗ"].geom
out["ŗ stem"] = comp("ŗ", below_x={"r": 1.0})
# 5. ĸ like K (arms meet the stem, no bar)
out["ĸ now"] = P["ĸ"].geom
out["ĸ K"] = finish(S((1, 0), (1, 10)) | S((6.5, 1, B), (2.5, 5), (6.5, 9, B)))
# 6. đ ħ: bar 2.5w each side of the stem; or stem poking 2w above the bar
d = RAW["d"]
out["đ now"] = P["đ"].geom
out["đ long"] = finish(d | S((3, -3), (9.5, -3)))
out["đ poke"] = finish(S((6, -6), (6, 10)) | S((6, 1), (1, 1), (1, 9), (6, 9)) | S((3, -3), (9, -3)))
h = shift(RAW["h"], 1.5)
out["ħ now"] = P["ħ"].geom
out["ħ long"] = finish(h | S((0, -3), (5.5, -3)))
out["ħ poke"] = finish(shift(S((1, -6), (1, 10)) | S((1, 1), (6, 1), (6, 10)), 1.5) | S((0, -3), (5.5, -3)))
# 7. ð: the current hooked ascender plus a short bar across it; or a slanted straight ascender with a bar
o = So((1, 1), (6, 1), (6, 9), (1, 9))
out["ð now"] = P["ð"].geom
out["ð bar"] = finish(o | S((6, 1), (6, -1.5), (3, -4, B)) | S((2.5, -1.5), (8, -1.5)))
out["ð slash"] = finish(o | S((6, 1), (6, -1.5), (3, -4, B)) | S((2.6, -0.2, B), (6.2, -4.2, B)))
out["ð d-bar"] = finish(o | S((6, 1), (6, -4)) | S((3.5, -3), (8.5, -3)))

for k, g in out.items():
    audit(k, g)
sheet(out, "proto.png", cols=12, scale=6, cell=(18, 32))
import pickle
pickle.dump(out, open(fr"{R}\proto.pkl", "wb"))
