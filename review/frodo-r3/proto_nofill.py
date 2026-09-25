"""Frodo r3 prototype: finish without the R0.5 inside fillet, i.e. soft(fill_pinches(raw)), vs the current finish.
Labels: U+E100 + 2k = current glyph, U+E101 + 2k = variant."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p, raw_p
from beadjoint.geom import soft, fill_pinches

CHARS = "TEHAPBRFmhnaesuv2458&#kKNxXyz±€¥£"
P, R = full_p(), raw_p()
GLYPHS = []
for k, c in enumerate(CHARS):
    GLYPHS.append((chr(0xE100 + 2 * k), P[c].geom))
    GLYPHS.append((chr(0xE101 + 2 * k), soft(fill_pinches(R[c]))))
