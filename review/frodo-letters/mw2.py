from _lib import *
exec(open(str(Path(__file__).resolve().parents[2] / "review/frodo-letters/mw.py"), encoding="utf-8").read().split("cand = {}")[0])

def M_hair(ym, W=10.0, r=2.0, rv=2.0):
    """One stroke up, down to the middle, up, down: hairpin shoulders (centreline r) so no wedge fills;
    the shoulder vertices are pushed up until the ink reaches the cap line."""
    xm = W / 2
    build = lambda d: S((1, 10), (1, -4 - d, r), (xm, ym, rv), (W - 1, -4 - d, r), (W - 1, 10))
    def top(d):
        try:
            return build(d).bounds[1]
        except ValueError:
            return -99
    lo, hi = 0.0, 4.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if top(mid) > -4:
            lo = mid
        else:
            hi = mid
    return build((lo + hi) / 2)

def W2V(r=1.0, W=11.0, apex=0.0):
    a = (W - 2) / 4
    return solve(lambda vy: S((1, -3, B), (1 + a, vy, r), (W / 2, apex, r), (W - 1 - a, vy, r), (W - 1, -3, B)), lo=9.5, hi=20)

cand = {
    "M v4 r1": M_v(4),
    "M v4 rv2": M_v(4, r=2),
    "M v5 rv2": M_v(5, r=2),
    "M v4 11w rv2": M_v(4, W=11, r=2),
    "M squared": P["M"].geom,
    "W 2V r1": W2V(),
    "W 2V apex2": W2V(apex=2.0),
    "W ^2 rv2": rotate180(M_v(4, r=2), (5, 3)),
}
sheet(cand, "mw2.png", refs="VN", cols=7, scale=11, cell=(16, 24))
