"""Frodo r3: the whole character set finished with acute.finish_acute (labels = the real characters)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import CHARS
import acute

A = acute.full_acute()
GLYPHS = [(c, A[c].geom) for c in CHARS]
