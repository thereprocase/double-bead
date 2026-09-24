"""Dump the colour moves of one glyph on one layer: feature, width, from -> to (glyph-local mm).

    cadpy dump.py --char "#" [--slice demo/slice] [--layout demo/layout.json] [--face top] [--layer N]
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import json
from pathlib import Path

from shapely import affinity
from shapely.geometry import shape

ROOT = Path("F:/code/beadjoint")
sys.path.insert(0, str(ROOT / "demo"))
sys.path.insert(0, "F:/code/masonry-keys")
import demo_check as dc  # noqa: E402

arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
sl = ROOT / arg("--slice", "demo/slice")
lay = json.loads((ROOT / arg("--layout", "demo/layout.json")).read_text(encoding="utf-8"))
face = arg("--face", "top")
_, _, total = dc.read_layers(sl / "plate_1.gcode", [])
layer = int(arg("--layer", str(total if face == "top" else 1)))
moves, walls, _ = dc.read_layers(sl / "plate_1.gcode", [layer])
sx, sy, ox, oy = dc.fit(walls, lay["size_mm"])
g = next(g for g in lay["glyphs"] if g["char"] == arg("--char", "#"))
geom = affinity.affine_transform(shape(g[face]), [sx, 0, 0, sy, ox, oy])
x0, y0, x1, y1 = geom.bounds
mv = [m for m in dc.near(dc.bucket(moves[layer]), (x0 - .3, y0 - .3, x1 + .3, y1 + .3)) if m[0] == "1"
      and x0 - .3 < m[1] < x1 + .3 and y0 - .3 < m[2] < y1 + .3]
print(f"glyph bbox {x1 - x0:.2f} x {y1 - y0:.2f} mm, layer {layer}, {len(mv)} colour moves")
for t, ax, ay, bx, by, w, f in mv:
    print(f"{f:12s} w {w:.3f}  ({ax - x0:6.3f},{ay - y0:6.3f}) -> ({bx - x0:6.3f},{by - y0:6.3f})  len {((bx-ax)**2+(by-ay)**2)**.5:.3f}")
