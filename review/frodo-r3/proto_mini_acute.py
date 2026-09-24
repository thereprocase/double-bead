"""Frodo r3 mini coupon, acute-only inside fillet (acute.finish_acute)."""
import sys
sys.path.insert(0, r"F:\code\beadjoint\review\frodo-r3")
sys.path.insert(0, r"F:\code\beadjoint")
import acute
from proto_mini_cur import MINI
A = acute.full_acute()
GLYPHS = [(c, A[c].geom) for c in MINI]
