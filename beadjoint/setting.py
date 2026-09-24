"""Setting (spec 9): optical pair offsets and the kerned, tabular and mixed settings.

Positions are glyph origins in w (the glyph's own x = 0), y down. A set line is a list of
(char, placed geometry, origin x).
"""
import unicodedata
from functools import lru_cache

import numpy as np
from shapely import affinity
from shapely.geometry import LineString

from .charset import ALIASES, full_m, full_mixed, full_p
from .glyphs import FIGURES

T = 2.4          # optical target gap = stem-to-stem gap
DEPTH = 3.0      # scanline cap = T + DEPTH
GAPMIN = 2.02     # hard true-distance floor: R9 says 2.0; +0.02 so a TTF (outlines rounded to 1/50 w)
                 # still passes the spec's 1.98 line check
WORD = 5.5       # word space, edge to edge (edges: see _edges)
WORD_FLOOR = 3.5 # true distance from a word to the whole previous word (Frodo r1)
CELL_M = 12      # monospace advance (= width(m) 10 + GAPMIN)
CELL_F = 9       # tabular figure advance (= 7 + GAPMIN)
N_SCAN = 101
BAND_X = (0.0, 10.0)
BAND_FIG = (-4.0, 10.0)


@lru_cache(maxsize=None)
def _profile(glyph, band):
    """Leftmost and rightmost ink on each of the N_SCAN scanlines of band (nan where none)."""
    ys = np.linspace(band[0], band[1], N_SCAN)
    x0, _, x1, _ = glyph.geom.bounds
    left = np.full(N_SCAN, np.nan)
    right = np.full(N_SCAN, np.nan)
    for i, y in enumerate(ys):
        hit = glyph.geom.intersection(LineString([(x0 - 1, y), (x1 + 1, y)]))
        if not hit.is_empty:
            b = hit.bounds
            left[i], right[i] = b[0], b[2]
    return left, right


def _mean_gap(ra, lb, dx):
    cap = T + DEPTH
    g = np.full(N_SCAN, cap)
    both = ~np.isnan(ra) & ~np.isnan(lb)
    g[both] = np.minimum(dx + lb[both] - ra[both], cap)
    return float(g.mean())


@lru_cache(maxsize=None)
def _simple(glyph):
    return glyph.geom.simplify(0.003)


def _distance(a, b, dx):
    return _simple(a).distance(affinity.translate(_simple(b), dx))


@lru_cache(maxsize=None)
def off(a, b):
    """Origin of b relative to origin of a: optical gap T on average, then the GAPMIN floor."""
    band = BAND_FIG if (a.tall or b.tall) else BAND_X
    _, ra = _profile(a, band)
    lb, _ = _profile(b, band)
    lo, hi = 0.0, 30.0
    if _mean_gap(ra, lb, lo) >= T:
        dx = lo                          # no root in [0, 30]: the floor below decides
    else:
        for _ in range(60):
            mid = (lo + hi) / 2
            if _mean_gap(ra, lb, mid) < T:
                lo = mid
            else:
                hi = mid
        dx = (lo + hi) / 2
    # Frodo r1: glyphs that share (almost) no scanline would stack (" over -, ' over .): keep their ink
    # boxes 1w apart; punctuation tucks under a letter by at most 1w ("car," must not read "bar;")
    if int((~np.isnan(ra) & ~np.isnan(lb)).sum()) < 5:
        dx = max(dx, a.maxx - b.minx + 1.0)
    if _punct(a) or _punct(b):
        dx = max(dx, a.maxx - b.minx - 1.0)
    # GAPMIN floor: the true distance grows no faster than dx, so stepping dx by the shortfall never
    # overshoots and converges from below in a few steps
    for _ in range(40):
        short = GAPMIN - _distance(a, b, dx)
        if short <= 1e-4:
            break
        dx += short + 1e-5
    # r7: two V-shaped sides meeting (vv, vw, wy, VW...) blur into the same notch as w's own; open them 0.6w
    if _vee(a) and _vee(b):
        dx += VEE_EXTRA
    # tuck limit (Beadjoint addition): ink boxes may overlap by at most (narrower width - 2w) / 2, so in
    # any run A B C the outer two stay 2w apart even when both tuck into B (a period can't be tucked into)
    overlap = a.maxx - (b.minx + dx)
    limit = max(0.0, (min(a.width, b.width) - GAPMIN) / 2)
    if overlap > limit:
        dx += overlap - limit
    return dx


VEE_EXTRA = 0.6


def _vee(g):
    return unicodedata.normalize("NFD", g.char)[0] in "vwyVWY"


def _punct(g):
    return unicodedata.category(g.char).startswith("P")


@lru_cache(maxsize=None)
def _edges(glyph):
    """Word-space edges (Frodo r1): halfway between the ink edge inside the band y in [-4, 10] and the
    bbox edge, so a descender overhang (j hook, ogonek) counts half and a cap-zone one fully."""
    left, right = _profile(glyph, BAND_FIG)
    bl = np.nanmin(left) if np.any(~np.isnan(left)) else glyph.minx
    br = np.nanmax(right) if np.any(~np.isnan(right)) else glyph.maxx
    return (bl + glyph.minx) / 2, (br + glyph.maxx) / 2


def _after_space(word, g, x):
    """Push glyph g (origin x) right until it is WORD_FLOOR from every glyph of the previous word."""
    for _ in range(40):
        placed = affinity.translate(_simple(g), x)
        short = max(WORD_FLOOR - placed.distance(affinity.translate(_simple(w), wx)) for w, wx in word)
        if short <= 1e-4:
            break
        x += short + 1e-5
    return x


def _word_start(word, g):
    """Origin for the first glyph g of a word after a space: its left edge WORD past the rightmost
    right edge of the whole previous word, then the WORD_FLOOR true-distance floor."""
    edge = max(wx + _edges(w)[1] for w, wx in word)
    return _after_space(word, g, edge + WORD - _edges(g)[0])


def _place(glyph, x):
    return glyph.char, affinity.translate(glyph.geom, x), x


def _prepare(text, glyphs):
    """Map aliases (no-break and thin spaces, hyphen variants, μ, ⌀); name every missing character at once."""
    text = "".join(ALIASES.get(c, c) for c in text)
    missing = sorted({c for c in text if c != " " and c not in glyphs})
    if missing:
        raise ValueError("Beadjoint has no glyph for " + ", ".join(f"{c!r} (U+{ord(c):04X})" for c in missing))
    return text


def _extra_spaces(glyphs, spaces):
    """Width added by each space after the first: the fonts' space advance (WORD - n-n ink gap)."""
    n = glyphs["n"]
    return (spaces - 1) * (WORD - (off(n, n) - n.maxx + n.minx)) if spaces > 1 else 0.0


def kerned(text, glyphs=None):
    """Set P: x_B = x_A + off(A, B); a word after a space starts WORD past the previous word's edge."""
    glyphs = glyphs or full_p()
    text = _prepare(text, glyphs)
    line, prev, prev_x, space, word = [], None, 0.0, 0, []
    for ch in text:
        if ch == " ":
            space += 1
            continue
        g = glyphs[ch]
        if prev is None:
            x = -g.minx
        elif space:
            x = _word_start(word, g) + _extra_spaces(glyphs, space)
            word = []
        else:
            x = prev_x + off(prev, g)
        line.append(_place(g, x))
        word.append((g, x))
        prev, prev_x, space = g, x, 0
    return line


def cell_origin(k, glyph, cell):
    return k * cell + (cell - glyph.width) / 2 - glyph.minx


def tabular(text, glyphs=None):
    """Set M: glyph k centred in cell k of CELL_M; a space is one empty cell."""
    glyphs = glyphs or full_m()
    text = _prepare(text, glyphs)
    return [_place(glyphs[ch], cell_origin(k, glyphs[ch], CELL_M)) for k, ch in enumerate(text) if ch != " "]


def mixed(text, glyphs=None):
    """Letters from P, figures from P with 1 -> 1ₜ: runs of figures on CELL_F cells, joined to
    letters by off(). A run after a space starts its first cell at the word-space edge."""
    glyphs = glyphs or full_mixed()
    text = _prepare(text, glyphs)
    line, prev, prev_x, space, i, word = [], None, 0.0, 0, 0, []
    while i < len(text):
        ch = text[i]
        if ch == " ":
            space, i = space + 1, i + 1
            continue
        if ch in FIGURES:
            j = i
            while j < len(text) and text[j] in FIGURES:
                j += 1
            run = [glyphs[c] for c in text[i:j]]
            if prev is None:
                run0 = 0.0
            elif space:          # Frodo r1: the first figure's edge, not its cell, starts the word
                run0 = _word_start(word, run[0]) + _extra_spaces(glyphs, space) - cell_origin(0, run[0], CELL_F)
                word = []
            else:
                run0 = prev_x + off(prev, run[0]) - cell_origin(0, run[0], CELL_F)
            for k, g in enumerate(run):
                x = run0 + cell_origin(k, g, CELL_F)
                line.append(_place(g, x))
                word.append((g, x))
                prev, prev_x = g, x
            i = j
        else:
            g = glyphs[ch]
            if prev is None:
                x = -g.minx
            elif space:
                x = _word_start(word, g) + _extra_spaces(glyphs, space)
                word = []
            else:
                x = prev_x + off(prev, g)
            line.append(_place(g, x))
            word.append((g, x))
            prev, prev_x = g, x
            i += 1
        space = 0
    return line


def ink_extent(line):
    """(min x, max x) of a set line's ink."""
    return min(g.bounds[0] for _, g, _ in line), max(g.bounds[2] for _, g, _ in line)
