"""Per-glyph validation of the demo slice: how every glyph actually prints.

    cadpy demo/demo_check.py [--slice demo/slice] [--tag name] [--crops demo/glyphs]

For each glyph, on the top face (last two layers) and the bed face (layers 1-2), from the gcode:
  covered    share of the glyph interior (outline eroded 0.03 mm) under colour (T1) beads
  void       largest letter area no colour bead reaches, away from the outline (glyph eroded
             0.04 mm, so outline raster noise does not count), mm^2
  bleed      colour more than 0.03 mm outside the glyph / glyph area
  intrude    body (T0) beads inside the glyph / glyph area
  widths     min / max colour bead width inside the glyph (mm, from ; LINE_WIDTH)
  single     colour beads at least 0.8 x the local stroke width where they run (local width = the
             largest disk inside the glyph that covers the bead's midpoint): a stroke printed as ONE
             bead, below the two-bead floor, counted as the length of such runs (mm; > 0.4 mm fails:
             a loop's short turnaround at a stroke tip is not a single-bead stroke). Wide beads at
             crossings and filled joints are two-bead.
  speck      largest void at least 0.05 mm wide on BOTH colour layers of a face: where the body colour
             shows through (Frodo r3; hairline seams where a loop's beads meet are not counted)
Pass: covered >= 97 %, speck <= 0.005 mm^2, wide void on either layer <= 0.02 mm^2, bleed <= 4 %,
single-bead runs <= 0.4 mm.
The gcode <-> coupon mapping is fitted from the body's outer wall at mid height.
Writes demo/check.json and, with --crops, a bead-level render per glyph and face.
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely import affinity
from shapely.geometry import Point, shape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "F:/code/masonry-keys")
from gcode_arcs import move_pieces  # noqa: E402

arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
RES = 0.01
SINGLE = 0.8
LT_STEPS = [0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0]
CELL = 5.0


def read_layers(gcode, want):
    L = gcode.read_text(encoding="utf-8", errors="ignore").splitlines()
    ex = next(i for i, l in enumerate(L) if l.startswith("; EXECUTABLE_BLOCK_START"))
    out = {n: [] for n in want}
    walls = []
    layer, tool, feat, x, y, w = 0, "0", "", 0.0, 0.0, 0.34
    total = sum(1 for l in L[ex:] if l.startswith("; CHANGE_LAYER"))
    mid = total // 2
    for l in L[ex:]:
        if l.startswith("; CHANGE_LAYER"):
            layer += 1
            continue
        if l.startswith("; FEATURE:"):
            feat = l.split(":", 1)[1].strip()
            continue
        if l.startswith("; LINE_WIDTH:"):
            w = float(l.split(":")[1])
            continue
        s = l.strip()
        if re.match(r"^T[0-9]$", s):
            tool = s[1]
            continue
        if not l.startswith(("G1 ", "G2 ", "G3 ")):
            continue
        pieces, nx, ny, e = move_pieces(l, x, y)
        if e > 0:
            if layer in out:
                out[layer] += [(tool, ax, ay, bx, by, w, feat) for ax, ay, bx, by in pieces]
            if layer == mid and tool == "0" and feat == "Outer wall":
                walls += [(ax, ay, w) for ax, ay, _, _ in pieces]
        x, y = nx, ny
    return out, walls, total


def fit(walls, size):
    """model (coupon mm) -> gcode: per-axis scale and offset from the outer wall bbox."""
    x0 = min(a - w / 2 for a, _, w in walls); x1 = max(a + w / 2 for a, _, w in walls)
    y0 = min(b - w / 2 for _, b, w in walls); y1 = max(b + w / 2 for _, b, w in walls)
    sx, sy = (x1 - x0) / size[0], (y1 - y0) / size[1]
    return sx, sy, x0, y0


def bucket(moves):
    grid = defaultdict(list)
    for m in moves:
        _, ax, ay, bx, by, _, _ = m
        for gx in range(int(min(ax, bx) // CELL), int(max(ax, bx) // CELL) + 1):
            for gy in range(int(min(ay, by) // CELL), int(max(ay, by) // CELL) + 1):
                grid[(gx, gy)].append(m)
    return grid


def near(grid, box):
    x0, y0, x1, y1 = box
    seen, out = set(), []
    for gx in range(int(x0 // CELL), int(x1 // CELL) + 1):
        for gy in range(int(y0 // CELL), int(y1 // CELL) + 1):
            for m in grid.get((gx, gy), ()):
                if id(m) not in seen:
                    seen.add(id(m))
                    out.append(m)
    return out


def raster_poly(geom, box):
    x0, y0, x1, y1 = box
    im = Image.new("1", (int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1), 0)
    d = ImageDraw.Draw(im)
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    for p in polys:
        d.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in p.exterior.coords], fill=1)
        for h in p.interiors:
            d.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in h.coords], fill=0)
    return np.array(im, bool)


def raster_beads(moves, tool, box):
    x0, y0, x1, y1 = box
    im = Image.new("1", (int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1), 0)
    d = ImageDraw.Draw(im)
    for t, ax, ay, bx, by, w, _ in moves:
        if t != tool:
            continue
        pa, pb = ((ax - x0) / RES, (y1 - ay) / RES), ((bx - x0) / RES, (y1 - by) / RES)
        r = w / 2 / RES
        d.line([pa, pb], fill=1, width=max(1, round(w / RES)))
        for px, py in (pa, pb):
            d.ellipse([px - r, py - r, px + r, py + r], fill=1)
    return np.array(im, bool)


MINW = 0.05


def wide(mask):
    """Pixels of mask in a part at least MINW wide (opening by a MINW disk): drops hairline seams."""
    r = MINW / 2 / RES
    core = ndimage.distance_transform_edt(mask) >= r
    return (ndimage.distance_transform_edt(~core) <= r) & mask


def largest(mask):
    lab, k = ndimage.label(mask)
    return float(ndimage.sum(mask, lab, range(1, k + 1)).max() * RES ** 2) if k else 0.0


def local_width(mask):
    """Per pixel: the largest LT_STEPS width t whose disk (radius t/2) fits in the glyph and covers
    the pixel (a stepped local thickness map, mm)."""
    edt = ndimage.distance_transform_edt(mask)
    out = np.zeros(mask.shape)
    for t in LT_STEPS:
        r = t / 2 / RES
        core = edt > r - 0.5
        opened = ndimage.distance_transform_edt(~core) <= r
        out[opened & mask] = t
    return out


def crop(moves, geom, box, path, mirror, S=40):
    x0, y0, x1, y1 = box
    X = (lambda x: (x1 - x) * S) if mirror else (lambda x: (x - x0) * S)
    Y = lambda y: (y1 - y) * S
    im = Image.new("RGB", (int((x1 - x0) * S) + 1, int((y1 - y0) * S) + 1), (236, 234, 228))
    d = ImageDraw.Draw(im)
    style = {"0": ((70, 72, 80), (40, 40, 46)), "1": ((250, 204, 40), (150, 110, 0))}
    for tool in ("0", "1"):
        for t, ax, ay, bx, by, w, _ in moves:
            if t != tool:
                continue
            r = w / 2 * S
            d.line([(X(ax), Y(ay)), (X(bx), Y(by))], fill=style[t][0], width=max(1, round(w * S)))
            for px, py in ((X(ax), Y(ay)), (X(bx), Y(by))):
                d.ellipse([px - r, py - r, px + r, py + r], fill=style[t][0])
        for t, ax, ay, bx, by, w, _ in moves:
            if t == tool:
                d.line([(X(ax), Y(ay)), (X(bx), Y(by))], fill=style[t][1], width=1)
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            d.line([(X(x), Y(y)) for x, y in ring.coords], fill=(40, 120, 255), width=1)
    im.save(path)


def main():
    sl = ROOT / arg("--slice", "demo/slice")
    lay = json.loads((ROOT / arg("--layout", "demo/layout.json")).read_text(encoding="utf-8"))
    crops = arg("--crops", None)
    if crops:
        crops = ROOT / crops
        crops.mkdir(parents=True, exist_ok=True)
    _, _, total = read_layers(sl / "plate_1.gcode", [])
    faces = {"top": (total - 1, total), "bottom": (1, 2)}
    moves, walls, _ = read_layers(sl / "plate_1.gcode", [1, 2, total - 1, total])
    sx, sy, ox, oy = fit(walls, lay["size_mm"])
    grids = {n: bucket(m) for n, m in moves.items()}
    report = {"fit": {"scale": [sx, sy], "offset": [ox, oy]}, "glyphs": {}}
    fails = []
    for g in lay["glyphs"]:
        c = g["char"]
        entry = {}
        for face, layers in faces.items():
            geom = affinity.affine_transform(shape(g[face]), [sx, 0, 0, sy, ox, oy])
            gx0, gy0, gx1, gy1 = geom.bounds
            box = (gx0 - 0.5, gy0 - 0.5, gx1 + 0.5, gy1 + 0.5)
            text = raster_poly(geom, box)
            inner = raster_poly(geom.buffer(-0.04), box)
            core = raster_poly(geom.buffer(-0.03), box)
            halo = raster_poly(geom.buffer(0.03), box)
            lw = local_width(text)
            area = max(text.sum(), 1)
            carea = max(core.sum(), 1)
            per, wides = [], []
            for n in layers:
                mv = near(grids[n], box)
                col = raster_beads(mv, "1", box)
                body = raster_beads(mv, "0", box)
                voids = inner & ~col
                big = largest(voids)
                wides.append(wide(voids))
                inside = geom.buffer(0.15)
                ws, single = [], 0.0
                for t, ax, ay, bx, by, w, _ in mv:
                    if t != "1" or not inside.contains(Point((ax + bx) / 2, (ay + by) / 2)):
                        continue
                    ws.append(w)
                    px = int(((ax + bx) / 2 - box[0]) / RES); py = int((box[3] - (ay + by) / 2) / RES)
                    if 0 <= py < lw.shape[0] and 0 <= px < lw.shape[1] and lw[py, px] >= 0.45 and w >= SINGLE * lw[py, px]:
                        single += math.hypot(bx - ax, by - ay)
                feats = sorted({f for t, ax, ay, bx, by, w, f in mv if t == "1" and inside.contains(Point((ax + bx) / 2, (ay + by) / 2))})
                per.append({"layer": n, "covered": round(100 * (core & col).sum() / carea, 2), "void": round(big, 4),
                            "bleed": round(100 * (col & ~halo).sum() / area, 2),
                            "intrude": round(100 * (body & text).sum() / area, 2),
                            "w_min": min(ws) if ws else None, "w_max": max(ws) if ws else None,
                            "fat": round(single, 3), "features": feats, "void_w": round(largest(wides[-1]), 4)})
                if crops and n in (total, 1):
                    crop(mv, geom, box, crops / f"{ord(c):04X}-{face}.png", mirror=(face == "bottom"))
            worst = {"covered": min(p["covered"] for p in per), "void": max(p["void"] for p in per),
                     "speck": round(largest(wides[0] & wides[1]), 4), "void_w": max(p["void_w"] for p in per),
                     "bleed": max(p["bleed"] for p in per), "fat": sum(p["fat"] for p in per),
                     "w_min": min((p["w_min"] for p in per if p["w_min"] is not None), default=None),
                     "w_max": max((p["w_max"] for p in per if p["w_max"] is not None), default=None)}
            worst["pass"] = bool(worst["covered"] >= 97 and worst["speck"] <= 0.005 and worst["void_w"] <= 0.02
                                 and worst["bleed"] <= 4 and worst["fat"] <= 0.4)
            entry[face] = {"layers": per, **worst}
            if not worst["pass"]:
                fails.append((c, face, worst))
        report["glyphs"][c] = entry
    report["fails"] = [{"char": c, "face": f, **w} for c, f, w in fails]
    tag = arg("--tag", "")
    (HERE / f"check{'-' + tag if tag else ''}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    allw = [(g[f]["w_min"], g[f]["w_max"]) for g in report["glyphs"].values() for f in ("top", "bottom") if g[f]["w_min"]]
    cov = [g[f]["covered"] for g in report["glyphs"].values() for f in ("top", "bottom")]
    print(f"fit scale {sx:.5f} {sy:.5f} offset {ox:.3f} {oy:.3f}")
    print(f"{len(report['glyphs'])} glyphs x 2 faces; covered min {min(cov):.1f}% median {sorted(cov)[len(cov) // 2]:.1f}%;"
          f" bead widths {min(a for a, _ in allw):.2f}..{max(b for _, b in allw):.2f} mm; fails {len(fails)}")
    for c, f, w in fails[:60]:
        print(f"  FAIL {c!r} U+{ord(c):04X} {f}: covered {w['covered']} void {w['void']} bleed {w['bleed']} fat {w['fat']}")


if __name__ == "__main__":
    main()
