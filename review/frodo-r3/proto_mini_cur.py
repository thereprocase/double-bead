"""Frodo r3 mini coupon, current finish: the tune.sh set plus the bed-face speck glyphs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p
MINI = "zwt#fXKNV&ł+ykvMWç“’*ÆH"
P = full_p()
GLYPHS = [(c, P[c].geom) for c in MINI]
