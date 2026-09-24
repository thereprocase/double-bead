"""Frodo r3: what a reader would actually see, per glyph and face, from a demo slice.

    cadpy analyze.py [--slice demo/slice] [--layout demo/layout.json] [--out review/frodo-r3/an-full.json] [--chars ...]

  speck     largest area (mm^2) void on BOTH colour layers of the face (body colour shows through), after
            dropping hairline seams: a void pixel counts only if the void is at least MINW (--minw, default 0.05 mm) wide there
  void_w    largest void (either layer) at least MINW wide, mm^2 (the checker's void minus hairline seams)
  hair      checker-style largest void including hairlines, mm^2
  thin      colour beads under 0.20 mm inside the glyph: total length mm, min width, features
  bleed_max farthest colour reaches outside the outline, mm (a blob or a bulge you can see)
  bite      largest glyph area within 0.10 mm of the outline that no colour bead covers, mm^2 (corner cut, rounded end)
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import json
from pathlib import Path

import numpy as np
from scipy import ndimage
from shapely import affinity
from shapely.geometry import Point, shape

ROOT = Path("F:/code/beadjoint")
sys.path.insert(0, str(ROOT / "demo"))
sys.path.insert(0, "F:/code/masonry-keys")
import demo_check as dc  # noqa: E402

arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
RES = dc.RES
MINW = float(arg("--minw", "0.05"))


def wide(mask):
    """Pixels of mask that lie in a part at least MINW wide (morphological opening by a MINW disk)."""
    r = MINW / 2 / RES
    edt = ndimage.distance_transform_edt(mask)
    core = edt >= r
    return (ndimage.distance_transform_edt(~core) <= r) & mask


def largest(mask):
    lab, k = ndimage.label(mask)
    return float(ndimage.sum(mask, lab, range(1, k + 1)).max() * RES ** 2) if k else 0.0


def main():
    sl = ROOT / arg("--slice", "demo/slice")
    lay = json.loads((ROOT / arg("--layout", "demo/layout.json")).read_text(encoding="utf-8"))
    chars = arg("--chars", None)
    _, _, total = dc.read_layers(sl / "plate_1.gcode", [])
    faces = {"top": (total - 1, total), "bottom": (1, 2)}
    moves, walls, _ = dc.read_layers(sl / "plate_1.gcode", [1, 2, total - 1, total])
    sx, sy, ox, oy = dc.fit(walls, lay["size_mm"])
    grids = {n: dc.bucket(m) for n, m in moves.items()}
    out = {}
    for g in lay["glyphs"]:
        c = g["char"]
        if chars and c not in chars:
            continue
        e = {}
        for face, layers in faces.items():
            geom = affinity.affine_transform(shape(g[face]), [sx, 0, 0, sy, ox, oy])
            gx0, gy0, gx1, gy1 = geom.bounds
            box = (gx0 - 0.5, gy0 - 0.5, gx1 + 0.5, gy1 + 0.5)
            text = dc.raster_poly(geom, box)
            inner = dc.raster_poly(geom.buffer(-0.04), box)
            rim = text & ~dc.raster_poly(geom.buffer(-0.10), box)
            dist_out = ndimage.distance_transform_edt(~text) * RES
            inside = geom.buffer(0.15)
            voids, hair, per = [], 0.0, {}
            thin_len, thin_min, thin_feat = 0.0, None, set()
            bleed_max, bite = 0.0, 0.0
            for n in layers:
                mv = dc.near(grids[n], box)
                col = dc.raster_beads(mv, "1", box)
                v = inner & ~col
                hair = max(hair, largest(v))
                vw = wide(v)
                voids.append(vw)
                per[n] = round(largest(vw), 4)
                bleed_max = max(bleed_max, float(dist_out[col].max()) if col.any() else 0.0)
                bite = max(bite, largest(rim & ~col))
                for t, ax, ay, bx, by, w, f in mv:
                    if t == "1" and w < 0.2 and inside.contains(Point((ax + bx) / 2, (ay + by) / 2)):
                        thin_len += ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
                        thin_min = w if thin_min is None else min(thin_min, w)
                        thin_feat.add(f)
            e[face] = {"speck": round(largest(voids[0] & voids[1]), 4), "void_w": max(per.values()), "per_layer": per,
                       "hair": round(hair, 4), "thin_len": round(thin_len, 3), "thin_min": thin_min,
                       "thin_feat": sorted(thin_feat), "bleed_max": round(bleed_max, 3), "bite": round(bite, 4)}
        out[c] = e
    p = ROOT / arg("--out", "review/frodo-r3/an-full.json")
    p.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    rows = [(c, f, v) for c, e in out.items() for f, v in e.items()]
    print("glyph-faces", len(rows))
    for key, lim in (("speck", 0.005), ("void_w", 0.02), ("thin_len", 0.3), ("bleed_max", 0.08), ("bite", 0.02)):
        bad = sorted(((v[key], c, f) for c, f, v in rows if v[key] > lim), reverse=True)
        print(f"{key} > {lim}: {len(bad)}  " + "  ".join(f"{c}U+{ord(c):04X}/{f[0]} {x}" for x, c, f in bad[:25]))


if __name__ == "__main__":
    main()
