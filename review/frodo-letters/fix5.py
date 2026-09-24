from _lib import *
from beadjoint.glyphs import _raw_p
from beadjoint.latin import capitals
from beadjoint.marks import apostrophe
p, cap = _raw_p(), capitals()
o = So((1, 1), (6, 1), (6, 9), (1, 9))
cand = {
    "ŀ now": P["ŀ"].geom,
    "ŀ dot y5": p["l"] | D((5, 5)),
    "ľ now": P["ľ"].geom,
    "ľ x5.6": p["l"] | apostrophe(5.6),
    "Ľ now": P["Ľ"].geom,
    "Ľ x5.6": cap["L"] | apostrophe(5.6),
    "ť now": P["ť"].geom,
    "ð now": P["ð"].geom,
    "ð bar": o | S((6, 1), (6, -1.5), (3, -4, B)) | S((2.5, -3, B), (7, -3)),
    "ð slash": o | S((6, 1), (6, -1.5), (3, -4, B)) | S((3.8, -1.2, B), (7.6, -3.9, B)),
    "ð straight": o | S((6, 1), (6, -3), (3.5, -4.5, B)) | S((4, -1.8, B), (8, -1.8, B)),
}
for k, g in cand.items():
    f = finish(g)
    print(k, "min gap between pieces", None if min_piece_gap(f) is None else round(min_piece_gap(f), 3))
sheet(cand, "fix5.png", refs="đd", cols=13, scale=9, cell=(14, 26))
