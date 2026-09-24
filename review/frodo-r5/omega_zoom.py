import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")

from beadjoint.geom import BALL as B, S, finish
from beadjoint.glyphs import Glyph
from beadjoint.sheet import grid

variants = {
    "v1_orig": S((0, 9, B), (2, 8, 1.5), (2, -3, 2), (6, -3, 2), (6, 8, 1.5), (8, 9, B)),
    "v2_wide": S((-0.5, 9, B), (1.5, 7, 1.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 7, 1.5), (8.5, 9, B)),
    "v3_wider_flat_feet": S((-1, 9, B), (1.5, 8, 1.5), (1.5, -3, 2), (7.5, -3, 2), (7.5, 8, 1.5), (10, 9, B)),
}
glyphs = {}
for name, raw in variants.items():
    g = finish(raw)
    print(name, "bounds", [round(b, 2) for b in g.bounds])
    glyphs[name] = Glyph(name, f"X:{name}", g)
grid(glyphs, r"F:\code\beadjoint\review\frodo-r5\omega_zoom.png", cols=3, scale=30)
