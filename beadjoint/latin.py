"""Beadjoint additions beyond the spec's sets (spec 12 extension rules): capitals, the ASCII and
Latin-1 symbols, and the special Latin letters. All geometry is raw (the finishing filter is
applied when the character set is assembled).

Conventions (w units, y down), shared with the spec's figures:
  capitals, figures and tall symbols    y in [-4, 10], bars on the 2-4-2-4-2 stack (centres -3, 3, 9)
  lowercase                             body [0, 10], ascenders to -4, descenders to 14
  small figures (superscripts, ordinals, fractions)  10w tall with the 2-2-2-2-2 stack (bars 1, 5, 9)
  every stroke 2w, every counter, aperture and gap between separate pieces >= 2w
"""
import math

from shapely import affinity
from shapely.ops import unary_union

from .geom import BALL as B, D, Rect, S, So, rotate180, solve


def mirror_x(g, width):
    """Mirror left-right within [0, width]."""
    return affinity.scale(g, -1, 1, origin=(width / 2, 0))


def shift(g, dx=0.0, dy=0.0):
    return affinity.translate(g, dx, dy)


def diagonal(x0, y0, x1, y1, clip=(-4.0, 10.0)):
    """2w diagonal (perpendicular width, R8) from (x0, y0) to (x1, y1), extended 1w past each end and
    cut flat on the horizontal lines y = clip."""
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    line = S((x0 - ux * 2, y0 - uy * 2), (x1 + ux * 2, y1 + uy * 2))
    return line.intersection(Rect(-20, clip[0], 40, clip[1]))


# --- small figures: the figure geometry with each 4w counter band squeezed to 2w --------------

def _squeeze_y(y):
    """Figure y in [-4, 10] -> small figure y in [0, 10]: stroke bands stay 2w, counters 4w -> 2w."""
    if y <= -2:
        return y + 4
    if y <= 2:
        return 2 + (y + 2) / 2
    if y <= 4:
        return y + 2
    if y <= 8:
        return 6 + (y - 4) / 2
    return y


def _squeeze_ring(coords):
    cuts = (-2.0, 2.0, 4.0, 8.0)
    out = []
    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        out.append((x0, y0))
        if y1 != y0:
            ts = sorted((c - y0) / (y1 - y0) for c in cuts if min(y0, y1) < c < max(y0, y1))
            out += [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t) for t in ts]
    out.append(coords[-1])
    return [(x, _squeeze_y(y)) for x, y in out]


def squeeze(g):
    from shapely.geometry import MultiPolygon, Polygon
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    out = [Polygon(_squeeze_ring(list(p.exterior.coords)), [_squeeze_ring(list(h.coords)) for h in p.interiors])
           for p in polys]
    return out[0] if len(out) == 1 else MultiPolygon(out)


def small_figures(fig):
    """Small figures (10w tall, x-height band [0, 10]) from the raw figures; 7 is redrawn (a
    squeezed diagonal would kink)."""
    s = {c: squeeze(fig[c]) for c in "0123456789" if c != "7"}
    s["7"] = S((0, 1), (6.4, 1, 1.6), (3.9, 9, B))
    s["1"] = S((1, 1, B), (3.5, 1), (3.5, 9)) | S((0.5, 9), (6.5, 9))
    return s


def _zigzag_n(r=0.8, width=9.0):
    """N as one stroke: up, diagonal down, up. A diagonal meeting a stem at an acute angle makes a
    3-3.5w blob in a 7w N, so the N is 9w wide and the bends are filleted (R5) and pushed out until
    the ink reaches the guides."""
    x1 = width - 1
    build = lambda d: S((1, 10), (1, -3 - d, r), (x1, 9 + d, r), (x1, -4))
    lo, hi = 0.0, 8.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if build(mid).bounds[1] > -4:
            lo = mid
        else:
            hi = mid
    return build((lo + hi) / 2)


def _pointed_m():
    """M: full stems and a V from the stem tops meeting at (5, 5) with a constant-width r = 2 hairpin,
    its centreline cut flat on the cap line (Frodo r1)."""
    v = S((0.293, -5.834), (5, 5, 2), (9.707, -5.834)).intersection(Rect(-20, -4, 40, 10))
    return S((1, 10), (1, -4)) | S((9, -4), (9, 10)) | v


def spokes(c, n, length, start_deg=-90.0):
    """n ball-ended spokes from a hub at c (Frodo r1 asterisk)."""
    g = D(c)
    for k in range(n):
        a = math.radians(start_deg + 360.0 * k / n)
        g = g | S(c, (c[0] + length * math.cos(a), c[1] + length * math.sin(a), B))
    return g


def capitals():
    c = {}
    # r12: legs straight up to the bar, then 5 degrees in (kink hidden by the bar) so A is not R; same 7 w as the
    # other capitals, the counter's top corners filleted inside
    lean = 6 * math.tan(math.radians(5))
    c["A"] = S((1, 10), (1, 3, 0), (1 + lean, -3, 1), (6 - lean, -3, 1), (6, 3, 0), (6, 10)) | S((1, 3), (6, 3))
    c["B"] = S((1, -4), (1, 10)) | S((1, -3), (5, -3), (5, 3), (1, 3)) | S((1, 3), (6, 3), (6, 9), (1, 9))
    c["C"] = S((6, -3, B), (1, -3, 2), (1, 9, 2), (6, 9, B))                   # r1: round like G and S
    c["D"] = So((1, -3, 0), (6, -3, 2), (6, 9, 2), (1, 9, 0))
    c["E"] = S((6.5, -3), (1, -3, 0), (1, 9, 0), (6.5, 9)) | S((1, 3), (5.5, 3))
    c["F"] = S((6.5, -3), (1, -3, 0), (1, 10)) | S((1, 3), (5.5, 3))
    c["G"] = S((6, -1, B), (6, -3), (1, -3, 2), (1, 9, 2), (6, 9), (6, 3), (4, 3))   # r1: hooked top, not a 6
    c["H"] = S((1, -4), (1, 10)) | S((6, -4), (6, 10)) | S((1, 3), (6, 3))
    c["I"] = S((3, -3), (3, 9)) | S((0, -3), (6, -3)) | S((0, 9), (6, 9))
    c["J"] = S((6, -4), (6, 9), (1, 9), (1, 6, B))
    c["K"] = S((1, -4), (1, 10)) | S((6.5, -3, B), (2.5, 3), (6.5, 9, B))     # r1: arms meet the stem, like k
    c["L"] = S((1, -4), (1, 9, 0), (6.5, 9))
    c["M"] = _pointed_m()                                                      # r1: pointed, like V (not a tall m)
    # r1: upright N, full stems, diagonal edges on the outer corners; finish() fills the wedges
    c["N"] = S((1, 10), (1, -4)) | S((8, -4), (8, 10)) | diagonal(1.111, -4, 7.889, 10)
    c["O"] = So((1, -3, 2), (8, -3, 2), (8, 9, 2), (1, 9, 2))
    c["P"] = S((1, -4), (1, 10)) | S((1, -3), (6, -3), (6, 3), (1, 3))
    c["Q"] = c["O"] | S((4.5, 9), (7, 12.5, B))
    c["R"] = c["P"] | S((3.5, 3), (6.5, 9, B))                                 # r1: straight leg, not an A
    c["S"] = S((6, -3, B), (1, -3, 2), (1, 2, 2), (6, 4, 2), (6, 9, 2), (1, 9, B))   # r1: round, slanted spine: not a 5
    c["T"] = S((0, -3), (7, -3)) | S((3.5, -3), (3.5, 10))
    c["U"] = S((1, -4), (1, 9), (6, 9), (6, -4))
    c["V"] = solve(lambda vy: S((1, -3, B), (4, vy, 1.0), (7, -3, B)), lo=9.5, hi=20)
    c["W"] = rotate180(_pointed_m(), (5, 3))                                   # r1: M turned over (not a Ш)
    c["X"] = S((1, -3, B), (7, 9, B)) | S((7, -3, B), (1, 9, B))
    c["Y"] = S((1, -3, B), (3.5, 2.5), (3.5, 10)) | S((6, -3, B), (3.5, 2.5))
    c["Z"] = S((0, -3), (6.3, -3, 0.8), (0.7, 9, 0.8), (7, 9))
    return c


def symbols(fig):
    """ASCII punctuation and symbols, Latin-1 and general-punctuation marks (raw geometry)."""
    s = {}
    head = D((1.7, -2.6), 1.4) | S((1.7, -2.6), (0.7, 0.4, B))     # r1: ’ with a head; ‘ is its mirror
    comma = shift(head, 0, 12)
    tick = S((1, -4), (1, -1, B))
    quote_r = head
    s["!"] = S((1, -4), (1, 5)) | D((1, 9))
    s['"'] = tick | shift(tick, 4)
    s["#"] = S((2, -3), (2, 9)) | S((6, -3), (6, 9)) | S((0, 0), (8, 0)) | S((0, 6), (8, 6))
    s["$"] = S((6, -2, B), (1, -2), (1, 3), (6, 3), (6, 8), (1, 8, B)) | S((3.5, -5), (3.5, -2)) | S((3.5, 8), (3.5, 11))
    s["%"] = D((1.75, -2.25), 1.75) | D((8.25, 8.25), 1.75) | diagonal(2.2, 10, 7.8, -4)   # r1: dots bigger than a period
    s["&"] = So((1.5, -3), (5.5, -3), (5.5, 1), (1.5, 1)) | S((3.5, 1), (1, 3.5, 1), (1, 9), (7, 9), (7, 4, B)) \
        | S((4.5, 1), (9, 10))
    s["'"] = tick
    s["("] = S((3.5, -5, B), (1, -2.5, 2), (1, 8.5, 2), (3.5, 11, B))
    s[")"] = mirror_x(s["("], 4.5)
    s["*"] = spokes((4.25, 0.4), 5, 3.4)                         # r1: five spokes, notch mouths exactly 2w
    s["+"] = S((0, 3), (6, 3)) | S((3, 0), (3, 6))
    s[","] = comma
    s["-"] = S((1, 3, B), (4, 3, B))
    s["."] = D((1, 9))
    rise, run = 14.0, 4.0
    half = math.hypot(rise, run) / rise
    s["/"] = diagonal(half, 10, half + run, -4)
    s[":"] = D((1, 1)) | D((1, 9))
    s[";"] = D((1.7, 1)) | comma
    s["<"] = S((6, -1, B), (1, 3), (6, 7, B))
    s["="] = S((0.5, 0.5), (6.5, 0.5)) | S((0.5, 5.5), (6.5, 5.5))
    s[">"] = mirror_x(s["<"], 7)
    s["?"] = S((1, -3, B), (6, -3), (6, 2), (3.5, 2), (3.5, 5)) | D((3.5, 9))
    s["@"] = S((5, 5), (9, 5), (9, -3), (1, -3), (1, 9), (8, 9, B)) | Rect(4, 0, 6, 5)
    s["["] = S((3.5, -5), (1, -5, 0), (1, 11, 0), (3.5, 11))
    s["\\"] = mirror_x(s["/"], s["/"].bounds[2] + s["/"].bounds[0])
    s["]"] = mirror_x(s["["], 3.5)
    s["^"] = S((1, 1, B), (3.5, -3.5), (6, 1, B))
    s["_"] = S((0, 13), (7, 13))
    s["`"] = S((1, -4, B), (2.8, -1.6, B))
    s["{"] = S((4.5, -5), (2.5, -5), (2.5, 1.5), (1, 3, 0.9), (2.5, 4.5), (2.5, 11), (4.5, 11))
    s["|"] = S((1, -5), (1, 11))
    s["}"] = mirror_x(s["{"], 4.5)
    s["~"] = S((0.5, 4, B), (2.5, 2), (4.5, 4), (6.5, 2, B))
    # Latin-1 punctuation and symbols
    s["¡"] = D((1, 1)) | S((1, 5), (1, 14))
    s["¿"] = rotate180(s["?"], (3.5, 5))
    s["¢"] = S((6, 1, B), (1, 1), (1, 9), (6, 9, B)) | S((3.5, -2), (3.5, 1)) | S((3.5, 9), (3.5, 12))
    s["£"] = S((6.5, -3, B), (3, -3), (3, 9)) | S((0.5, 9), (7, 9)) | S((0.5, 3), (5, 3))
    s["¤"] = shift(So((2, 0), (6, 0), (6, 4), (2, 4)) | S((0.3, -1.7, B), (1.6, -0.4)) | S((7.7, -1.7, B), (6.4, -0.4))
                   | S((0.3, 5.7, B), (1.6, 4.4)) | S((7.7, 5.7, B), (6.4, 4.4)), 0, 1)   # r1: centred on y = 3
    s["¥"] = S((1, -3, B), (3.5, 1.5), (3.5, 10)) | S((6, -3, B), (3.5, 1.5)) | S((0.5, 5.5), (6.5, 5.5))
    s["¦"] = S((1, -5), (1, 1.5)) | S((1, 4.5), (1, 11))
    s["§"] = S((6, -4, B), (1, -4), (1, 0), (6, 0), (6, 6)) | S((1, 0), (1, 6), (6, 6), (6, 10), (1, 10, B))   # r1: not a 5
    s["©"] = So((1, -4, 2), (13, -4, 2), (13, 10, 2), (1, 10, 2)) | S((9, 0, B), (5, 0), (5, 6), (9, 6, B))
    s["®"] = So((1, -4, 2), (15, -4, 2), (15, 10, 2), (1, 10, 2)) | S((5, 7), (5, -1)) \
        | S((5, 0), (10, 0), (10, 4), (5, 4)) | diagonal(8.5, 4, 10.5, 7, clip=(3, 7))
    s["¬"] = S((0, 3), (6, 3), (6, 6.5))                          # r1: bar on the math axis
    s["°"] = So((1, -3, 2), (6, -3, 2), (6, 2, 2), (1, 2, 2))      # r1: round ring, 3w hole (was a dot at label size)
    s["±"] = S((0, 1), (6, 1)) | S((3, -2), (3, 4)) | S((0, 8), (6, 8))
    s["µ"] = S((1, 0), (1, 14)) | S((1, 9), (6, 9)) | S((6, 0), (6, 10))
    s["¶"] = S((5, -3), (5, 10)) | S((9, -3), (9, 10)) | S((9, -3), (1, -3), (1, 3), (5, 3))
    s["·"] = D((1, 3))
    s["×"] = S((0.5, 0.5, B), (5.5, 5.5, B)) | S((0.5, 5.5, B), (5.5, 0.5, B))
    s["÷"] = S((0, 3), (6, 3)) | D((3, -1)) | D((3, 7))
    s["«"] = S((4, 0, B), (1, 3), (4, 6, B)) | S((9.8, 0, B), (6.8, 3), (9.8, 6, B))
    s["»"] = mirror_x(s["«"], 10.8)
    s["‹"] = S((4, 0, B), (1, 3), (4, 6, B))
    s["›"] = mirror_x(s["‹"], 5)
    s["–"] = S((0, 3), (7, 3))
    s["—"] = S((0, 3), (14, 3))
    s["−"] = S((0, 3), (6, 3))
    s["‘"] = mirror_x(head, 2.4)
    s["’"] = quote_r
    s["‚"] = comma
    s["“"] = s["‘"] | shift(s["‘"], 5.0)
    s["”"] = quote_r | shift(quote_r, 5.0)
    s["„"] = comma | shift(comma, 5.0)
    s["′"] = S((1.8, -4), (1, -1, B))
    s["″"] = s["′"] | shift(s["′"], 4.4)
    s["†"] = S((3, -4), (3, 12)) | S((0, -0.5), (6, -0.5))
    s["‡"] = S((3, -4), (3, 12)) | S((0, -1.5), (6, -1.5)) | S((0, 7.5), (6, 7.5))
    s["•"] = D((2, 3), 2)                                        # r1: clearly bigger than ·
    s["…"] = D((1, 9)) | D((5, 9)) | D((9, 9))
    s["€"] = S((7, -3, B), (2, -3), (2, 9), (7, 9, B)) | S((0, 1), (5.5, 1)) | S((0, 5), (5.5, 5))
    s["‰"] = s["%"] | D((14.0, 8.25), 1.75)
    s["⁄"] = s["/"]
    # r5: labels need these (10kΩ, flow direction, limits)
    # r11: the r7 splayed legs read as 人; the bowl now pinches in to two legs with flat feet, O's corners
    s["Ω"] = S((-1, 9), (2.5, 9, 0), (2.5, 6, 1), (1, 4, 1), (1, -3, 2), (8, -3, 2), (8, 4, 1), (6.5, 6, 1),
               (6.5, 9, 0), (10, 9))
    s["→"] = S((0, 3, B), (7, 3)) | S((3, -1, B), (7, 3), (3, 7, B))
    s["←"] = mirror_x(s["→"], s["→"].bounds[2] + s["→"].bounds[0])
    s["↓"] = S((3, 0, B), (3, 7)) | S((-1, 3, B), (3, 7), (7, 3, B))
    s["↑"] = S((3, 7, B), (3, 0)) | S((-1, 3, B), (3, 0), (7, 3, B))
    s["≤"] = S((5, -2, B), (1, 1), (5, 4, B)) | S((1, 8), (5, 8))
    s["≥"] = mirror_x(s["≤"], s["≤"].bounds[2] + s["≤"].bounds[0])
    s["≈"] = shift(s["~"], 0, -3) | shift(s["~"], 0, 3)
    s["≠"] = s["="] | S((2, 9), (5, -3))                                            # r12
    s["₺"] = S((3, -4), (3, 9, 2), (8.5, 9, 2), (8.5, 4.5, B)) | S((0.5, 1.5), (5.5, 0)) | S((0.5, 6), (5.5, 4.5))   # r12
    small = small_figures(fig)
    raised = {k: shift(v, 0, -4) for k, v in small.items()}
    s["¹"], s["²"], s["³"] = raised["1"], raised["2"], raised["3"]
    frac_slash = diagonal(0.9, 10, 4.9, -4)
    for ch, (n, d) in {"¼": ("1", "4"), "½": ("1", "2"), "¾": ("3", "4"),
                       "⅛": ("1", "8"), "⅜": ("3", "8"), "⅝": ("5", "8"), "⅞": ("7", "8"),   # r5: eighths
                       "⅓": ("1", "3"), "⅔": ("2", "3")}.items():                                     # r12: thirds
        num = raised[n]
        sl = shift(frac_slash, num.bounds[2] + 1.2)
        den = shift(small[d], sl.bounds[2] + 1.2 - small[d].bounds[0])
        s[ch] = unary_union([num, sl, den])
    return s


def specials(p, cap, sym):
    """Special Latin letters (Latin-1, Latin Extended-A) that are not base + mark."""
    x = {}
    x["ı"] = S((1, 0), (1, 10))
    x["ȷ"] = S((4, 0), (4, 13), (1, 13, B))
    x["ß"] = S((1, 10), (1, -3, 2), (5.5, -3), (5.5, 2)) | S((4, 2), (6.5, 2), (6.5, 9), (5, 9, B))   # r1: not a B
    x["æ"] = S((1, 1, B), (5, 1), (5, 10)) | S((5, 5), (1, 5), (1, 9), (5, 9)) \
        | S((5, 5), (9.5, 5), (9.5, 1), (5, 1)) | S((5, 9), (9.5, 9, B))
    x["œ"] = S((5, 1), (1, 1), (1, 9), (5, 9)) | S((5, 1), (5, 9)) \
        | S((5, 5), (9.5, 5), (9.5, 1), (5, 1)) | S((5, 9), (9.5, 9, B))
    x["Æ"] = S((1, 10), (1, -3), (10.5, -3)) | S((5.5, -3), (5.5, 9, 0), (10.5, 9)) | S((1, 3), (9.5, 3))
    x["Œ"] = S((10.5, -3), (1, -3, 2), (1, 9, 2), (10.5, 9)) | S((5.5, -3), (5.5, 9)) | S((5.5, 3), (9.5, 3))
    x["ð"] = So((1, 1), (6, 1), (6, 9), (1, 9)) | S((6, 1), (6, -1.5), (3, -4, B))
    x["Ð"] = shift(cap["D"], 1.5) | S((0, 3), (4.5, 3))
    x["Đ"] = x["Ð"]
    x["đ"] = S((6, -6), (6, 10)) | S((6, 1), (1, 1), (1, 9), (6, 9)) | S((3, -3), (9, -3))   # r2: stem pokes above the bar
    x["þ"] = S((1, -4), (1, 14)) | S((1, 1), (6, 1), (6, 9), (1, 9))
    x["Þ"] = S((1, -4), (1, 10)) | S((1, 0), (6, 0), (6, 6), (1, 6))
    # slashes cross the straight sides (a slash through a rounded corner makes a 3w+ blob)
    # ø: at x-height a slash through the 6w counter leaves pinched islands, so it passes behind the o
    x["ø"] = shift(So((1, 1), (7, 1), (7, 9), (1, 9)) | S((6.2, 2.6), (8.8, -0.8, B)) | S((1.8, 7.4), (-0.8, 10.8, B)), 1.8)
    x["Ø"] = So((1, -3, 2), (8, -3, 2), (8, 9, 2), (1, 9, 2)) | S((-0.5, 7.29), (9.5, -1.29))
    bar = S((0, 5.5, B), (5, 0.5, B))
    x["ł"] = shift(shift(p["l"], 1.5) | bar, 1)
    x["Ł"] = shift(shift(cap["L"], 1.5) | bar, 1)
    x["ħ"] = shift(S((1, -6), (1, 10)) | S((1, 1), (6, 1), (6, 10)), 1.5) | S((0, -3), (5.5, -3))   # r2: not ћ
    x["Ħ"] = shift(cap["H"], 1) | S((0, -1), (9, -1))
    x["ŧ"] = p["t"] | S((0.5, 5), (5, 5))
    x["Ŧ"] = cap["T"] | S((1, 3), (6, 3))
    x["ĸ"] = S((1, 0), (1, 10)) | S((1, 5), (3.5, 5)) | S((6.5, 1, B), (3.5, 5), (6.5, 9, B))
    x["ŋ"] = S((1, 10), (1, 1, 0), (6, 1), (6, 13), (3.5, 13, B))
    x["Ŋ"] = S((1, 10), (1, -3, 0), (6, -3), (6, 13), (3.5, 13, B))
    x["ŀ"] = p["l"] | D((5, 5))                                  # r1: middle dot at mid x-height
    x["Ŀ"] = cap["L"] | D((5, 3))
    x["ſ"] = S((2.5, 10), (2.5, -3), (5.5, -3, B))
    x["ƒ"] = S((7, -3, B), (4.5, -3, 2), (2.5, 13, 2), (0, 13, B)) | S((1.5, 1), (6.5, 1))         # r12: slanted stem
    # r12: capital sharp s: sharp top right, diagonal to a rounded U-turn at mid height, tail ball 2 w off the stem
    x["ẞ"] = S((1, 10), (1, -3, 2), (7.5, -3, 0.5), (3.8, 2.5, 1.3), (8, 2.5, 1.5), (8, 9, 2), (5, 9, B))
    x["ĳ"] = p["i"] | shift(p["j"], 1)
    x["Ĳ"] = cap["I"] | shift(cap["J"], 8)
    x["ª"] = shift(p["a"], 0, -4)
    x["º"] = shift(p["o"], 0, -4)
    x["™"] = shift(S((0, 1), (6, 1)) | S((3, 1), (3, 10)), 0, -4) \
        | shift(S((1, 10), (1, 1, 0), (9, 1, 0), (9, 10)) | S((5, 1), (5, 7, B)), 8, -4)
    return x


def mono_narrow():
    """r12: Mono versions of glyphs whose proportional forms are wider than Mono's 10 w ink limit."""
    m = {}
    m["æ"] = S((1, 1, B), (5, 1), (5, 10)) | S((5, 5), (1, 5), (1, 9), (5, 9)) \
        | S((5, 5), (9, 5), (9, 1), (5, 1)) | S((5, 9), (9, 9, B))
    m["œ"] = S((5, 1), (1, 1), (1, 9), (5, 9)) | S((5, 1), (5, 9)) | S((5, 5), (9, 5), (9, 1), (5, 1)) | S((5, 9), (9, 9, B))
    m["Æ"] = S((1, 10), (1, -3), (10, -3)) | S((5, -3), (5, 9, 0), (10, 9)) | S((1, 3), (9, 3))
    m["Œ"] = S((10, -3), (1, -3, 2), (1, 9, 2), (10, 9)) | S((5, -3), (5, 9)) | S((5, 3), (9, 3))
    # ø: the proportional ring with stubs cut to 1 w past it; Ø: its 40 degree slash shortened
    m["ø"] = So((2, 1), (8, 1), (8, 9), (2, 9)) | S((7.2, 2.6), (9, 0.24, B)) | S((2.8, 7.4), (1, 9.76, B))
    u = (0.759, -0.651)
    m["Ø"] = So((1, -3, 2), (8, -3, 2), (8, 9, 2), (1, 9, 2)) \
        | S((4.5 - 5.6 * u[0], 3 - 5.6 * u[1]), (4.5 + 5.6 * u[0], 3 + 5.6 * u[1]))
    m["«"] = S((3.5, 0, B), (1, 3), (3.5, 6, B)) | S((8.7, 0, B), (6.2, 3), (8.7, 6, B))
    m["»"] = mirror_x(m["«"], m["«"].bounds[2] + m["«"].bounds[0])
    m["—"] = S((0, 3), (10, 3))
    m["Ĳ"] = S((1, -4), (1, 10)) | S((9, -4), (9, 9, 2), (5, 9, B))
    m["Ω"] = S((-0.5, 9), (2.5, 9, 0), (2.5, 6, 1), (1, 4, 1), (1, -3, 2), (8, -3, 2), (8, 4, 1), (6.5, 6, 1),
               (6.5, 9, 0), (9.5, 9))
    return m


def square_w():
    """r12: w as a turned m with a short middle stick (top at y = 4), matching u and m; the V-built w read as a u
    with a bump and filled its valleys solid (3.5 w). 10 w wide, so Mono uses it unchanged."""
    return S((1, 0), (1, 9), (9, 9), (9, 0)) | S((5, 9), (5, 4))
