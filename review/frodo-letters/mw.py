from _lib import *

def edge_c(dx_total, rise):
    """Horizontal half-width c of a 2w diagonal whose centreline runs (c, 0) -> (dx_total - c, rise)."""
    c = 1.0
    for _ in range(40):
        c = math.hypot(dx_total - 2 * c, rise) / rise
    return c

def M_v(ym, W=10.0, r=1.0):
    """Stems at the edges; a V whose arms leave the stem tops flush (lower edge through the outer
    top corner) and meet at (W/2, ym) with a centreline fillet r."""
    xm = W / 2
    # left arm: lower-left edge through (0,-4); centreline top at (c, -4)
    c = 1.0
    for _ in range(40):
        dx, dy = xm - c, ym + 4
        L = math.hypot(dx, dy)
        c = L / dy          # horizontal half-width of the arm at the cut
    dx, dy = xm - c, ym + 4
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    v = S((c - ux * 2, -4 - uy * 2), (xm, ym, r), (W - c + ux * 2, -4 - uy * 2)).intersection(Rect(-20, -4, 40, 20))
    return S((1, 10), (1, -4)) | S((W - 1, -4), (W - 1, 10)) | v

def W_v(ym, W=10.0, r=1.0):
    return rotate180(M_v(6 - ym, W, r), (W / 2, 3))

cand = {}
for ym in (3, 4, 5, 6):
    cand[f"M v{ym}"] = M_v(ym)
cand["M squared (now)"] = P["M"].geom
for ym in (3, 2, 1):
    cand[f"W ^{ym}"] = W_v(ym)
cand["W squared (now)"] = P["W"].geom
cand["W 2V"] = solve(lambda vy: S((1, -3, B), (3.3, vy, 1.0), (5.5, 0), (7.7, vy, 1.0), (10, -3, B)), lo=9.5, hi=20)
sheet(cand, "mw.png", refs="VHN", cols=7, scale=11, cell=(16, 24))
