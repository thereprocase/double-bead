"""Frodo r3: zoomed bead render of chosen glyphs from a demo slice, with problems marked.

    python3 zoom.py --chars "WMN" [--slice demo/slice] [--layout demo/layout.json] [--face top|bottom]
                    [--layer N] [--S 120] [--out review/frodo-r3/z] [--stats]

Colour beads yellow, body beads grey; colour beads under 0.20 mm drawn red, over 0.45 mm magenta;
unfilled glyph interior (void) painted cyan; body bead pixels inside the glyph painted orange.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import Point, shape

ROOT = Path("F:/code/beadjoint")
sys.path.insert(0, str(ROOT / "demo"))
sys.path.insert(0, "F:/code/masonry-keys")
import demo_check as dc  # noqa: E402
import json  # noqa: E402

arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def main():
    sl = ROOT / arg("--slice", "demo/slice")
    lay = json.loads((ROOT / arg("--layout", "demo/layout.json")).read_text(encoding="utf-8"))
    face = arg("--face", "top")
    S = float(arg("--S", "120"))
    out = ROOT / arg("--out", "review/frodo-r3/z")
    out.mkdir(parents=True, exist_ok=True)
    chars = arg("--chars", "")
    _, _, total = dc.read_layers(sl / "plate_1.gcode", [])
    layer = int(arg("--layer", str(total if face == "top" else 1)))
    moves, walls, _ = dc.read_layers(sl / "plate_1.gcode", [layer])
    sx, sy, ox, oy = dc.fit(walls, lay["size_mm"])
    grid = dc.bucket(moves[layer])
    for g in lay["glyphs"]:
        c = g["char"]
        if c not in chars:
            continue
        geom = affinity.affine_transform(shape(g[face]), [sx, 0, 0, sy, ox, oy])
        gx0, gy0, gx1, gy1 = geom.bounds
        box = (gx0 - 0.4, gy0 - 0.4, gx1 + 0.4, gy1 + 0.4)
        mv = dc.near(grid, box)
        mirror = face == "bottom"
        x0, y0, x1, y1 = box
        X = (lambda x: (x1 - x) * S) if mirror else (lambda x: (x - x0) * S)
        Y = lambda y: (y1 - y) * S
        im = Image.new("RGB", (int((x1 - x0) * S) + 1, int((y1 - y0) * S) + 1), (236, 234, 228))
        d = ImageDraw.Draw(im)
        for tool in ("0", "1"):
            for t, ax, ay, bx, by, w, _ in mv:
                if t != tool:
                    continue
                col = (70, 72, 80) if t == "0" else ((230, 40, 40) if w < 0.2 else (220, 60, 220) if w > 0.45 else (250, 204, 40))
                r = w / 2 * S
                d.line([(X(ax), Y(ay)), (X(bx), Y(by))], fill=col, width=max(1, round(w * S)))
                for px, py in ((X(ax), Y(ay)), (X(bx), Y(by))):
                    d.ellipse([px - r, py - r, px + r, py + r], fill=col)
        # voids and body intrusion, from the checker's rasters
        text = dc.raster_poly(geom, box)
        inner = dc.raster_poly(geom.buffer(-0.04), box)
        colr = dc.raster_beads(mv, "1", box)
        body = dc.raster_beads(mv, "0", box)
        arr = np.array(im)
        vo = inner & ~colr
        bi = dc.raster_poly(geom.buffer(-0.06), box) & body
        # raster grid is RES=0.01 mm, unmirrored; map to image
        ys, xs = np.nonzero(vo)
        for yy, xx in zip(ys, xs):
            px = (x1 - (x0 + xx * dc.RES)) * S if mirror else xx * dc.RES * S
            py = yy * dc.RES * S
            arr[int(py):int(py + dc.RES * S) + 1, int(px):int(px + dc.RES * S) + 1] = (0, 220, 240)
        ys, xs = np.nonzero(bi)
        for yy, xx in zip(ys, xs):
            px = (x1 - (x0 + xx * dc.RES)) * S if mirror else xx * dc.RES * S
            py = yy * dc.RES * S
            arr[int(py):int(py + dc.RES * S) + 1, int(px):int(px + dc.RES * S) + 1] = (255, 130, 0)
        im = Image.fromarray(arr)
        d = ImageDraw.Draw(im)
        for t, ax, ay, bx, by, w, _ in mv:
            if t == "1":
                d.line([(X(ax), Y(ay)), (X(bx), Y(by))], fill=(120, 80, 0), width=1)
        polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
        for p in polys:
            for ring in [p.exterior, *p.interiors]:
                d.line([(X(x), Y(y)) for x, y in ring.coords], fill=(40, 120, 255), width=2)
        name = f"{ord(c):04X}-{face}-L{layer}.png"
        im.save(out / name)
        if "--stats" in sys.argv:
            inside = geom.buffer(0.15)
            thin = [(round(w, 3), f, round((ax + bx) / 2 - gx0, 2), round((ay + by) / 2 - gy0, 2), round(((bx - ax) ** 2 + (by - ay) ** 2) ** .5, 3))
                    for t, ax, ay, bx, by, w, f in mv if t == "1" and w < 0.24 and inside.contains(Point((ax + bx) / 2, (ay + by) / 2))]
            print(c, face, layer, "void px", int(vo.sum()), "body-in px", int(bi.sum()), "thin beads(<0.24):", len(thin),
                  "len", round(sum(x[4] for x in thin), 3), thin[:6])
        print("wrote", out / name)


if __name__ == "__main__":
    main()
