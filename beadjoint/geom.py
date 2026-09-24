"""Beadjoint geometry primitives (spec sections 5, 6 and 8).

Units are extrusion widths (w) and y points down, as in the spec: x-height line y = 0,
baseline y = 10, figure top y = -4. Every stroke is 2w: a centreline buffered by 1.
"""
import math

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

BALL = "ball"                  # endpoint tag (x, y, BALL): adds a unit disk (spec: ●)
ARC_STEP = math.radians(1.5)   # fillet arcs: chord error under 0.0004w at r = 2
QS = 64                        # quad_segs for disks and round offsets


def D(c, r=1.0):
    """Disk of radius r about c."""
    return Point(c).buffer(r, quad_segs=QS)


def Rect(x0, y0, x1, y1):
    """Axis-aligned box."""
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _unit(x, y):
    n = math.hypot(x, y)
    return x / n, y / n


def fillet(a, p, b, r):
    """Replace vertex p (between neighbours a and b) by an arc of centreline radius r.

    Returns (points from the a-side tangent point to the b-side one, tangent length t).
    r = 0 keeps the sharp vertex (the stroke then gets a mitre join there)."""
    ux, uy = _unit(a[0] - p[0], a[1] - p[1])
    vx, vy = _unit(b[0] - p[0], b[1] - p[1])
    theta = math.acos(max(-1.0, min(1.0, ux * vx + uy * vy)))
    if r == 0 or theta > math.pi - 1e-9:
        return [p], 0.0
    t = r / math.tan(theta / 2)
    bx, by = _unit(ux + vx, uy + vy)
    d = r / math.sin(theta / 2)
    cx, cy = p[0] + d * bx, p[1] + d * by
    a0 = math.atan2(p[1] + uy * t - cy, p[0] + ux * t - cx)
    a1 = math.atan2(p[1] + vy * t - cy, p[0] + vx * t - cx)
    sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi      # the short way: |sweep| = pi - theta
    n = max(2, math.ceil(abs(sweep) / ARC_STEP))
    return [(cx + r * math.cos(a0 + sweep * i / n), cy + r * math.sin(a0 + sweep * i / n))
            for i in range(n + 1)], t


def _parse(pts):
    xy = [(float(p[0]), float(p[1])) for p in pts]
    tags = [p[2] if len(p) > 2 else None for p in pts]
    return xy, tags


def _radius(tag):
    if tag == BALL:
        raise ValueError("BALL is an endpoint tag; interior vertices take a fillet radius")
    return 1.0 if tag is None else float(tag)


def _check_tangents(xy, ts, closed):
    """Two fillets must not overrun the segment between them."""
    n = len(xy)
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        seg = math.dist(xy[i], xy[j])
        if ts[i] + ts[j] > seg + 1e-9:
            raise ValueError(f"fillets overrun segment {xy[i]} -> {xy[j]}: {ts[i]:.3f} + {ts[j]:.3f} > {seg:.3f}")


def S(*pts):
    """Open stroke S[p0, p1^r, ..., pn].

    Interior vertices are filleted with centreline radius r (default 1; 0 = sharp mitre), the
    centreline is buffered by 1 with flat caps and mitre joins, and endpoints tagged BALL get D(p, 1)."""
    xy, tags = _parse(pts)
    if len(xy) < 2:
        raise ValueError("a stroke needs two points")
    line, ts = [xy[0]], [0.0]
    for i in range(1, len(xy) - 1):
        arc, t = fillet(xy[i - 1], xy[i], xy[i + 1], _radius(tags[i]))
        line += arc
        ts.append(t)
    line.append(xy[-1])
    ts.append(0.0)
    _check_tangents(xy, ts, closed=False)
    g = LineString(line).buffer(1.0, cap_style="flat", join_style="mitre", mitre_limit=5.0)
    for i in (0, len(xy) - 1):
        if tags[i] == BALL:
            g = g.union(D(xy[i]))
        elif tags[i] is not None:
            raise ValueError("endpoints take no fillet radius")
    return g


def So(*pts):
    """Closed stroke S°[...]: every vertex filleted, the loop buffered by 1 to both sides.

    Built as offset(+1) minus offset(-1) of the filleted loop, so the outer corners come out
    R(r+1) and the inner ones R(r-1) (sharp for the default r = 1)."""
    xy, tags = _parse(pts)
    n = len(xy)
    ring, ts = [], []
    for i in range(n):
        arc, t = fillet(xy[i - 1], xy[i], xy[(i + 1) % n], _radius(tags[i]))
        ring += arc
        ts.append(t)
    _check_tangents(xy, ts, closed=True)
    c = Polygon(ring)
    return c.buffer(1.0, join_style="mitre", mitre_limit=5.0).difference(
        c.buffer(-1.0, join_style="mitre", mitre_limit=5.0))


def soft(g, r=0.5):
    """Finishing filter (spec 6): morphological opening with a disk of radius r."""
    return g.buffer(-r, quad_segs=QS).buffer(r, quad_segs=QS)


PINCH_R = 0.98      # closing radius: negative space narrower than 1.96w is a pinch
PINCH_MIN_AREA = 0.5


def fill_pinches(g, r=PINCH_R, min_area=PINCH_MIN_AREA):
    """Fill every pinch in a glyph's negative space: the spec's 'tight' pieces (closing at r = 0.98
    minus the glyph, eroded 0.03, area > 0.5 w^2). Counters, apertures and gaps of 2w or more stay
    open, and so do plain 90-degree inside corners (0.2 w^2); acute wedges (N, v, k, x, y, z joints)
    and near-touching pieces are filled. Two beads of body colour cannot print a narrower slit."""
    g = _clean(g)
    closed = _clean(g.buffer(r, quad_segs=QS).buffer(-r, quad_segs=QS))
    extra = _robust(lambda **k: closed.difference(g, **k))
    core = extra.buffer(-0.03)                     # erode first: hairline slivers must not join pieces
    polys = list(core.geoms) if hasattr(core, "geoms") else [core]
    keep = [q for q in polys if not q.is_empty and q.area > min_area]
    fills = [_robust(lambda **k: unary_union(keep).buffer(0.06, quad_segs=QS).intersection(extra, **k))] if keep else []
    if not fills:
        return g
    out = _robust(lambda **k: g.union(unary_union(fills), **k))
    return out.buffer(1e-3, join_style="mitre").buffer(-1e-3, join_style="mitre")    # seal hairline seams


def _clean(g):
    """Valid polygonal geometry (buffer(0) repairs self-touching rings from unions of arcs)."""
    from shapely import make_valid
    g = g if g.is_valid else make_valid(g)
    return g.buffer(0)


def _robust(op):
    """Run a GEOS overlay; on a precision failure retry snapped to a 1e-6 w grid."""
    from shapely.errors import GEOSException
    try:
        return op()
    except GEOSException:
        return op(grid_size=1e-6)


FILLET_MIN_AREA = 0.1


def fillet_inside(g, r=0.5, min_area=FILLET_MIN_AREA):
    """R0.5 inside fillets only where they seal a notch, slit or pinhole (Frodo r3). A fillet in an open
    right-angle or obtuse corner (small piece whose mouth to the negative space is wide) is left out:
    it swelled every crossing from 2.83 to 3.22w and every T from 2.5 to 2.75w, and the one-wall top
    layer printed that as 0.52 mm beads pushing colour 0.1 mm past the outline."""
    g = _clean(g)
    closed = _clean(g.buffer(r, quad_segs=QS).buffer(-r, quad_segs=QS))
    extra = _robust(lambda **k: closed.difference(g, **k))
    polys = list(extra.geoms) if hasattr(extra, "geoms") else [extra]
    gb = g.buffer(1e-3)
    keep = []
    for p in polys:
        if p.is_empty or p.area < 1e-6:
            continue
        mouth = p.boundary.difference(gb).length              # boundary shared with the negative space
        if not (p.area <= min_area and mouth > 1.2 * p.area ** 0.5):   # skip open corners, keep notches
            keep.append(p)
    if not keep:
        return g
    out = _robust(lambda **k: g.union(unary_union(keep), **k))
    return out.buffer(1e-3, join_style="mitre").buffer(-1e-3, join_style="mitre")


def finish(g):
    """Glyph finishing: fill pinches, round inside corners R0.5, then the spec's soft filter
    (opening, r = 0.5) rounds outside corners R0.5."""
    return soft(fillet_inside(fill_pinches(g)))


def rotate180(g, about):
    return affinity.rotate(g, 180, origin=about)


def solve(build, target=10.0, lo=9.5, hi=16.0, iters=60):
    """Find vy in [lo, hi] such that the lowest ink of build(vy) sits on y = target (spec 5)."""
    f = lambda vy: build(vy).bounds[3] - target
    if f(lo) > 0 or f(hi) < 0:
        raise ValueError("solve: target not bracketed")
    for _ in range(iters):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return build((lo + hi) / 2)


# --- monospace widening (spec 8) -------------------------------------------------------------

WIDEN_CUTS = (2.0, 5.0)


def widen_x(x):
    """Stretch only the counter zone: stems in x <= 2 stay, 2..5 grows to 2..7, x >= 5 moves +2."""
    if x <= 2:
        return x
    if x < 5:
        return 2 + (x - 2) * 5 / 3
    return x + 2


def _widen_ring(coords):
    out = []
    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        out.append((x0, y0))
        if x1 != x0:
            ts = sorted((c - x0) / (x1 - x0) for c in WIDEN_CUTS if min(x0, x1) < c < max(x0, x1))
            out += [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t) for t in ts]
    out.append(coords[-1])
    return [(widen_x(x), y) for x, y in out]


def widen(g):
    """Piecewise-linear x map applied exactly: edges are split at the zone boundaries first,
    so straight edges stay straight within each zone and the map keeps the topology."""
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    out = [Polygon(_widen_ring(list(p.exterior.coords)), [_widen_ring(list(h.coords)) for h in p.interiors])
           for p in polys if not p.is_empty]
    return out[0] if len(out) == 1 else MultiPolygon(out)
