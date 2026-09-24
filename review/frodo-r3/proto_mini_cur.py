"""Frodo r3 mini coupon, current finish: the tune.sh set plus the bed-face speck glyphs."""
import sys
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_p
MINI = "zwt#fXKNV&ł+ykvMWç“’*ÆH"
P = full_p()
GLYPHS = [(c, P[c].geom) for c in MINI]
