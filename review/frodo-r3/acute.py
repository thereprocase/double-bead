"""Frodo r3 prototype: the inside-corner fillet only where it fills a notch (acute), not at right-angle
corners, T-junctions, crossings and bends (there its 0.054 w^2 pieces only fatten the junction:
crossings 2.83 -> 3.22 w, T-junctions 2.5 -> 2.75 w, which the one-wall top layer prints as 0.52 mm
beads bulging 0.10-0.14 mm past the outline).

    fillet_inside_acute(g, r=0.5, min_area=0.1): drops closing pieces that are open corners (area <= min_area
    and a wide mouth: mouth length > 1.2 sqrt(area)); notches (area > min_area), slits and pinholes are kept
    (a corner of angle a adds r^2 (cot(a/2) - (pi - a)/2): 90 deg 0.054, 70 deg 0.11, 60 deg 0.17 w^2)
"""
import sys
sys.path.insert(0, r"F:\code\beadjoint")
from shapely.ops import unary_union

from beadjoint import charset
from beadjoint.geom import QS, _clean, _robust, fill_pinches, soft

MIN_AREA = 0.1


def fillet_inside_acute(g, r=0.5, min_area=MIN_AREA):
    g = _clean(g)
    closed = _clean(g.buffer(r, quad_segs=QS).buffer(-r, quad_segs=QS))
    extra = _robust(lambda **k: closed.difference(g, **k))
    polys = list(extra.geoms) if hasattr(extra, "geoms") else [extra]
    gb = g.buffer(1e-3)
    keep = []
    for p in polys:
        if p.is_empty or p.area < 1e-6:
            continue
        mouth = p.boundary.difference(gb).length        # boundary shared with the negative space
        corner = p.area <= min_area and mouth > 1.2 * p.area ** 0.5   # an open right-angle/obtuse corner
        if not corner:                                   # notches, slits and pinholes are still sealed
            keep.append(p)
    if not keep:
        return g
    out = _robust(lambda **k: g.union(unary_union(keep), **k))
    return out.buffer(1e-3, join_style="mitre").buffer(-1e-3, join_style="mitre")


def finish_acute(g):
    return soft(fillet_inside_acute(fill_pinches(g)))


def full_acute():
    """The whole P set assembled with finish_acute (monkeypatched into charset, caches cleared)."""
    old = charset.finish
    charset.finish = finish_acute
    charset.full_p.cache_clear()
    try:
        return charset.full_p()
    finally:
        charset.finish = old
        charset.full_p.cache_clear()
