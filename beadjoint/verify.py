"""Verification (spec 11): raster checks of every glyph, the pieces of a glyph, and neighbour distances
in set lines. What python build.py enforces with these is listed in spec 11.

    thickness(g) = 2 * max(EDT(g)) / 40            per piece; strokes <= 2.85 (R2), R11 dots excepted
    thin(g)      = pieces of g - open(g, 0.98), eroded 0.03, area > 0.5 w^2      require none
    tight(g)     = pieces of close(g, 0.98) - g, same filter                       informational
    piece gap    = true distance between separate pieces of a glyph             >= 1.98
    line check   = dist(neighbour_i, neighbour_i+1) >= 1.98

Morphology uses exact Euclidean distance transforms (erode: EDT(g) > r, dilate: EDT(~g) <= r),
so a disk of radius 0.98 costs the same as any other.
"""
import math

import numpy as np
import shapely
from scipy import ndimage

RES = 40            # px per w
MAX_T = 2.85        # R2, for the strokes of the spec sets
# The font families' glyphs are finished with geom.finish (spec 6), which fills acute joins solid, so
# their ink runs past R2. The designed maxima are the filled arrow tips (← → ↓ 4.84), V (4.75) and
# N (4.54); the 4w bullet measures 3.97. The small margin above 4.84 only absorbs raster rounding: a
# slab like v0.1.1's fused ĳ (5.5) fails, and fused_pieces is what catches pieces joined by finishing.
SHIPPED_MAX_T = 4.85
DOT_FILL = 1.1      # a piece whose area is under 1.1x that of its inscribed disk is a dot (R11)
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


def piece_thickness(geom, res=RES):
    """[(thickness, area)] for each separate piece of ink, from one raster."""
    mask = raster(geom, res)
    edt = ndimage.distance_transform_edt(mask)
    lab, n = ndimage.label(mask)
    idx = np.arange(1, n + 1)
    return [(2 * float(t) / res, float(a) / res ** 2)
            for t, a in zip(ndimage.maximum(edt, lab, idx), ndimage.sum(mask, lab, idx))]


def is_dot(thickness, area):
    """A piece is an R11 dot when its area is (close to) that of its own inscribed disk."""
    return area < DOT_FILL * math.pi * (thickness / 2) ** 2


def stroke_thickness(geom, res=RES):
    """Largest thickness of any piece that is not an R11 dot (0 for a glyph of dots only)."""
    return max((t for t, a in piece_thickness(geom, res) if not is_dot(t, a)), default=0.0)


def _pieces(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def piece_gap(geom):
    """Smallest true distance between separate pieces of geom (inf for a single piece)."""
    ps = _pieces(geom)
    return min((a.distance(b) for i, a in enumerate(ps) for b in ps[i + 1:]), default=math.inf)


# Joins that finishing makes by design, per family: the spec's Mono k (spec 8) stops its arm 0.25w short
# of the stem, and fill_pinches fills that notch tip, which R3 allows at acute joins.
FUSED_BY_DESIGN = {"M": frozenset("k")}


def fused_pieces(glyphs, inputs):
    """{char: [input pieces held by each finished piece]} for every glyph whose finishing joined pieces its
    input kept apart. glyphs: {char: Glyph} finished; inputs: {char: geometry} as finishing received it
    (charset.finish_inputs). fill_pinches fills gaps under 1.96w, so pieces drawn too close merge."""
    from shapely import make_valid
    out = {}
    for c, g in glyphs.items():
        raw = inputs[c]
        parts = _pieces((raw if raw.is_valid else make_valid(raw)).buffer(0))
        counts = [sum(1 for q in parts if f.distance(q) < 1e-9) for f in _pieces(g.geom)]
        if max(counts, default=0) > 1:
            out[c] = counts
    return out


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
