"""Frodo r3 prototype: crossings with sharp inside corners (no R0.5 inside fillet) vs the current finish.
Labels: U+E000 + 2k = current glyph, U+E001 + 2k = variant (soft() only: crossing 2.83 w instead of 3.22 w)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p, raw_p
from beadjoint.geom import soft, fill_pinches

CHARS = "tf+#Ħ×"
P, R = full_p(), raw_p()
GLYPHS = []
for k, c in enumerate(CHARS):
    GLYPHS.append((chr(0xE000 + 2 * k), P[c].geom))
    GLYPHS.append((chr(0xE001 + 2 * k), soft(fill_pinches(R[c]))))
