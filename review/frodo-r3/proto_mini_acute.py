"""Frodo r3 mini coupon, acute-only inside fillet (acute.finish_acute)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acute
from proto_mini_cur import MINI
A = acute.full_acute()
GLYPHS = [(c, A[c].geom) for c in MINI]
