"""Frodo's symbol prototypes (raw geometry in the latin.py notation), checked and drawn."""
import math
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from shapely.ops import unary_union
from beadjoint.geom import S, So, D, finish, rotate180, BALL as B
from beadjoint.latin import diagonal, mirror_x, shift, squeeze
from beadjoint.verify import check_glyph
from beadjoint.glyphs import Glyph, pieces
from beadjoint.charset import full_mixed

R = r"F:\code\beadjoint\review\frodo-symbols"


def spokes(c, n, length, start_deg=-90.0):
    """n ball-ended 2w spokes of centreline length `length` from centre c (angles from +x, y down)."""
    g = D(c)
    for k in range(n):
        a = math.radians(start_deg + 360.0 * k / n)
        g = g | S(c, (c[0] + length * math.cos(a), c[1] + length * math.sin(a), B))
    return g


def top_at(g, y=-4.0):
    """Shift so the top of the ink sits on y (cap line)."""
    return shift(g, 0, y - g.bounds[1])


def star():
    return {
        "* now (x-shape)": S((0.5, -3.5, B), (5.5, 1.5, B)) | S((0.5, 1.5, B), (5.5, -3.5, B)),
        "* 3-spoke L3.2": top_at(spokes((3.8, 0), 3, 3.2)),
        "* 5-spoke L3.2": top_at(spokes((4, 0), 5, 3.2)),
        "* 5-spoke L4": top_at(spokes((5, 0), 5, 4.0)),
        "* 6-spoke L3": top_at(spokes((4, 0), 6, 3.0)),
        "* 6-spoke L4": top_at(spokes((5, 0), 6, 4.0)),
    }


def quotes():
    q = {}
    now = S((1.5, -3, B), (0.7, -0.2, B))
    q["’ now"] = now
    q["‘ now"] = rotate180(now, (1.1, -1.6))
    head = D((1.7, -2.6), 1.4) | S((1.7, -2.6), (0.7, 0.4, B))                  # Q1: 2.8w head + 2w tail
    q["’ Q1 head"] = head
    q["‘ Q1 head"] = rotate180(head, (1.2, -1.3))
    bent = S((2.2, -4), (2.2, -2.2, 1.0), (0.8, 0.6, B))                         # Q2: '9' bend
    q["’ Q2 bent"] = bent
    q["‘ Q2 bent"] = rotate180(bent, (1.5, -1.5))
    q["’ Q4 mirror"] = now
    q["‘ Q4 mirror"] = mirror_x(now, 2.2)                                        # Q4: opposite slant
    q["’ Q5 head+mirror"] = head
    q["‘ Q5 head+mirror"] = mirror_x(head, 2.4)
    return q


if __name__ == "__main__":
    from beadjoint.sheet import grid
    for name, cands, cols in (("star", star(), 6), ("quotes", quotes(), 10)):
        out = {}
        for k, g in cands.items():
            f = finish(g)
            r = check_glyph(f)
            b = f.bounds
            print(f"{k:22} T={r['thickness']:.2f} thin={r['thin']} islands={r['islands']} "
                  f"x[{b[0]:.2f},{b[2]:.2f}] y[{b[1]:.2f},{b[3]:.2f}] pieces={len(pieces(f))}")
            out[k] = Glyph(k[0], k, f)
        grid(out, fr"{R}\{name}.png", cols=cols, scale=10, cell=(18, 24))


# --- final proposals -----------------------------------------------------------------------------

def small_one():
    """Small 1 with the tabular 1's base (the squeezed 1ₜ): flag y=1, base y=9."""
    return S((1, 1, B), (3.5, 1), (3.5, 9)) | S((0.5, 9), (6.5, 9))


def fractions(small1):
    fig = full_mixed()
    from beadjoint.charset import raw_p
    from beadjoint.latin import small_figures
    from beadjoint import glyphs as spec
    small = small_figures(spec._raw_p())
    small["1"] = small1
    raised = {k: shift(v, 0, -4) for k, v in small.items()}
    frac_slash = diagonal(0.9, 10, 4.9, -4)
    out = {"¹": raised["1"]}
    for ch, (n, d) in {"¼": ("1", "4"), "½": ("1", "2"), "¾": ("3", "4")}.items():
        num = raised[n]
        sl = shift(frac_slash, num.bounds[2] + 1.2)
        den = shift(small[d], sl.bounds[2] + 1.2 - small[d].bounds[0])
        out[ch] = unary_union([num, sl, den])
    return out


def proposals():
    p = {}
    p["*"] = top_at(spokes((4.4, 0), 5, 3.4))                                   # 5-spoke, notch mouth 2.0w
    head = D((1.7, -2.6), 1.4) | S((1.7, -2.6), (0.7, 0.4, B))                  # ’ : 2.8w head, 2w tail
    p["’"] = head
    p["‘"] = mirror_x(head, 2.4)
    p[","] = shift(head, 0, 12)
    p["°"] = So((1, -3, 2), (6, -3, 2), (6, 2, 2), (1, 2, 2))                   # 7x7 ring, 3x3 round hole
    p["•"] = D((2, 3), 2)                                                        # 4w disk (· is 2w)
    p["%"] = D((1.75, -2.25), 1.75) | D((8.25, 8.25), 1.75) | diagonal(2.2, 10, 7.8, -4)
    p["§"] = S((6, -4, B), (1, -4), (1, 0), (6, 0), (6, 6)) | S((1, 0), (1, 6), (6, 6), (6, 10), (1, 10, B))
    p["¬"] = S((0, 3), (6, 3), (6, 6.5))
    p["¤"] = shift(So((2, 0), (6, 0), (6, 4), (2, 4)) | S((0.3, -1.7, B), (1.6, -0.4)) | S((7.7, -1.7, B), (6.4, -0.4))
                   | S((0.3, 5.7, B), (1.6, 4.4)) | S((7.7, 5.7, B), (6.4, 4.4)), 0, 1)
    p.update(fractions(small_one()))
    return p


def proposals_all():
    """Proposals plus the glyphs derived from them."""
    p = proposals()
    p["‚"] = p[","]
    p["“"] = p["‘"] | shift(p["‘"], 5.0)
    p["”"] = p["’"] | shift(p["’"], 5.0)
    p["„"] = p[","] | shift(p[","], 5.0)
    p[";"] = D((1.7, 1)) | p[","]
    p["‰"] = p["%"] | D((14.0, 8.25), 1.75)             # dot gap 2.25w
    return p
