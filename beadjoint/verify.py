"""Verification (spec 11): raster checks of every glyph and neighbour distances in set lines.

    thickness(g) = 2 * max(EDT(g)) / 40            require <= 2.85 (2.83 at crossings)
    thin(g)      = pieces of g - open(g, 0.98), eroded 0.03, area > 0.5 w^2      require none
    tight(g)     = pieces of close(g, 0.98) - g, same filter                       informational
    line check   = dist(neighbour_i, neighbour_i+1) >= 1.98

Morphology uses exact Euclidean distance transforms (erode: EDT(g) > r, dilate: EDT(~g) <= r),
so a disk of radius 0.98 costs the same as any other.
"""
import math

import numpy as np
import shapely
from scipy import ndimage

RES = 40            # px per w
MAX_T = 2.85
THIN_R = 0.98
ERODE = 0.03
MIN_AREA = 0.5      # w^2
LINE_MIN = 1.98


def raster(geom, res=RES, pad=2.0):
    """Boolean mask of pixel centres inside geom (row 0 = smallest y)."""
    minx, miny, maxx, maxy = geom.bounds
    x0, y0 = minx - pad, miny - pad
    w = int(math.ceil((maxx - minx + 2 * pad) * res))
    h = int(math.ceil((maxy - miny + 2 * pad) * res))
    xs = x0 + (np.arange(w) + 0.5) / res
    ys = y0 + (np.arange(h) + 0.5) / res
    X, Y = np.meshgrid(xs, ys)
    return shapely.contains_xy(geom, X, Y)


def erode(mask, r, res=RES):
    return ndimage.distance_transform_edt(mask) > r * res


def dilate(mask, r, res=RES):
    return ndimage.distance_transform_edt(~mask) <= r * res


def opening(mask, r, res=RES):
    return dilate(erode(mask, r, res), r, res)


def closing(mask, r, res=RES):
    return erode(dilate(mask, r, res), r, res)


def _big_pieces(mask, res=RES):
    lab, n = ndimage.label(erode(mask, ERODE, res))
    if not n:
        return []
    areas = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) / res ** 2
    return [round(float(a), 3) for a in areas if a > MIN_AREA]


def check_glyph(geom, res=RES, thin_r=THIN_R):
    mask = raster(geom, res)
    edt = ndimage.distance_transform_edt(mask)
    thick = 2 * float(edt.max()) / res
    iy, ix = np.unravel_index(int(np.argmax(edt)), edt.shape)
    minx, miny = geom.bounds[0] - 2.0, geom.bounds[1] - 2.0
    where = (round(minx + (ix + 0.5) / res, 2), round(miny + (iy + 0.5) / res, 2))
    thin = _big_pieces(mask & ~opening(mask, thin_r, res), res)
    gaps = closing(mask, thin_r, res) & ~mask
    tight = _big_pieces(gaps, res)
    # a thin island: a narrow piece of negative space enclosed by ink (cannot print in body colour)
    holes = ndimage.binary_fill_holes(mask) & ~mask
    islands = _big_pieces(gaps & holes, res)
    return {"thickness": round(thick, 3), "at": where, "thin": thin, "tight": tight, "islands": islands,
            "two_bead": thick <= MAX_T, "ok": not thin and not islands}


def check_set(glyphs):
    """{char: result} for every glyph of a set."""
    return {c: check_glyph(g.geom) for c, g in glyphs.items()}


def line_gaps(placed, window=3):
    """True distances in a set line between each glyph and the next `window` glyphs (Frodo r1: a
    neighbours-only check let a_b print b on a): [(a, b, dist)]."""
    out = []
    for i, (ca, ga) in enumerate(placed):
        for cb, gb in placed[i + 1:i + 1 + window]:
            out.append((ca, cb, float(ga.distance(gb))))
    return out
