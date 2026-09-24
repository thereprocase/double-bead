"""Frodo r3: the whole character set finished with acute.finish_acute (labels = the real characters)."""
import sys
sys.path.insert(0, r"F:\code\beadjoint\review\frodo-r3")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import CHARS
import acute

A = acute.full_acute()
GLYPHS = [(c, A[c].geom) for c in CHARS]
