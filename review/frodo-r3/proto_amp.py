"""Frodo r3: & variants. U+E200 current, U+E201 C (arm leans right and crosses the tail), U+E202 B (no right arm),
U+E203 C with the acute-only inside fillet."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p
from beadjoint.geom import BALL as B, S, So, finish
import acute

loop = So((1.5, -3), (5.5, -3), (5.5, 1), (1.5, 1))
C = loop | S((3.5, 1), (1, 3.5, 1), (1, 9), (5, 9), (8.5, 4.5, B)) | S((4.5, 1), (9, 10))
Bv = loop | S((3.5, 1), (1, 3.5, 1), (1, 9), (6.5, 9, B)) | S((4.5, 1), (9, 10))
GLYPHS = [("\ue200", full_p()["&"].geom), ("\ue201", finish(C)), ("\ue202", finish(Bv)), ("\ue203", acute.finish_acute(C))]
