"""Frodo r3: quote head radius 1.4 (current) vs 1.25 vs 1.6, three copies each (placement noise)."""
import sys
sys.path.insert(0, r"F:\code\beadjoint\review\frodo-r3")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.geom import BALL as B, D, S
import acute
GLYPHS = []
for k, r in enumerate((1.4, 1.25, 1.6)):
    head = D((1.7, -2.6), r) | S((1.7, -2.6), (0.7, 0.4, B))
    for j in range(3):
        GLYPHS.append((chr(0xE300 + 16 * k + j), acute.finish_acute(head)))
