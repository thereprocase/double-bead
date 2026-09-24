"""Round breve (r = 2.4: t = 2.5 exactly leaves zero-length end segments and a broken flat cap),
ĸ as k without the ascender, Å/Ů options."""
from _lib import *
from proto import comp, FIN, RAW, NEW, P

NEW["breve"] = S((0, 0, B), (0, 2.5, 2.4), (5, 2.5, 2.4), (5, 0, B))
out = {}
for c in "ăĂğĞŭŬ":
    out[c + " now"] = P[c].geom
    out[c + " rnd"] = comp(c, NEW)
out["k now"] = P["k"].geom
out["ĸ now"] = P["ĸ"].geom
out["ĸ k"] = finish(S((1, 0), (1, 10)) | S((6, 1, B), (2.5, 6), (6.5, 9, B)))
out["ĸ k5"] = finish(S((1, 0), (1, 10)) | S((6, 1, B), (2.5, 5.5), (6.5, 9, B)))
for k, g in out.items():
    audit(k, g)
sheet(out, "proto2.png", cols=8, scale=6, cell=(18, 32))
