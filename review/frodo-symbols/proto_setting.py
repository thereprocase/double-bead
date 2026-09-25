"""Frodo's setting prototype: setting.off() plus a stacked-pair guard, and word spaces measured
optically (side bearings against n) instead of bbox ink-to-ink. Mirrors setting.kerned/mixed."""
import sys
from pathlib import Path
from functools import lru_cache
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from beadjoint.charset import full_mixed, full_p
from beadjoint.glyphs import FIGURES
from beadjoint.setting import BAND_FIG, BAND_X, CELL_F, T, WORD, _place, _profile, cell_origin, off

SHARED_MIN = 5      # scanlines (of 101) both glyphs must ink for the optical gap to mean anything
STACK_GAP = 1.0     # bbox gap for stacked pairs (ink at disjoint heights: -. ". _ °- .* ...)
WORD_MIN = 3.5      # bbox floor of a word space, from the rightmost ink of the whole previous word


def shared(a, b):
    band = BAND_FIG if (a.tall or b.tall) else BAND_X
    _, ra = _profile(a, band)
    lb, _ = _profile(b, band)
    return int((~np.isnan(ra) & ~np.isnan(lb)).sum())


PUNCT_TUCK = 1.0    # punctuation never nests deeper than this under/over a neighbour (car, vs bar;)


def _punct(g):
    import unicodedata
    return unicodedata.category(g.char).startswith("P")


@lru_cache(maxsize=None)
def off2(a, b):
    dx = off(a, b)
    if shared(a, b) < SHARED_MIN:
        dx = max(dx, a.maxx - b.minx + STACK_GAP)
    if _punct(a) or _punct(b):
        dx = max(dx, a.maxx - b.minx - PUNCT_TUCK)
    return dx


def inkgap2(a, b):
    return off2(a, b) - a.maxx + b.minx


@lru_cache(maxsize=None)
def word_dx(a, b, n):
    """Origin offset across a space: optical side bearings against n, plus WORD - n|n gap."""
    nn = inkgap2(n, n)
    return a.maxx + (inkgap2(a, n) - nn / 2) + (WORD - nn) + (inkgap2(n, b) - nn / 2) - b.minx


def kerned2(text, glyphs=None):
    glyphs = glyphs or full_p()
    n = glyphs["n"]
    line, prev, prev_x, space, right = [], None, 0.0, False, -1e9
    for ch in text:
        if ch == " ":
            space = True
            continue
        g = glyphs[ch]
        if prev is None:
            x = -g.minx
        elif space:
            x = max(prev_x + word_dx(prev, g, n), right + WORD_MIN - g.minx)
        else:
            x = prev_x + off2(prev, g)
        right = x + g.maxx if space or prev is None else max(right, x + g.maxx)
        line.append(_place(g, x))
        prev, prev_x, space = g, x, False
    return line


def mixed2(text, glyphs=None):
    glyphs = glyphs or full_mixed()
    n = glyphs["n"]
    line, prev, prev_x, space, i, right = [], None, 0.0, False, 0, -1e9
    while i < len(text):
        ch = text[i]
        if ch == " ":
            space, i = True, i + 1
            continue
        if ch in FIGURES:
            j = i
            while j < len(text) and text[j] in FIGURES:
                j += 1
            run = [glyphs[c] for c in text[i:j]]
            if prev is None:
                run0 = 0.0
            else:
                if space:
                    x0 = max(prev_x + word_dx(prev, run[0], n), right + WORD_MIN - run[0].minx)
                else:
                    x0 = prev_x + off2(prev, run[0])
                run0 = x0 - cell_origin(0, run[0], CELL_F)
            for k, g in enumerate(run):
                x = run0 + cell_origin(k, g, CELL_F)
                right = x + g.maxx if (k == 0 and (space or prev is None)) else max(right, x + g.maxx)
                line.append(_place(g, x))
                prev, prev_x = g, x
            i = j
        else:
            g = glyphs[ch]
            if prev is None:
                x = -g.minx
            elif space:
                x = max(prev_x + word_dx(prev, g, n), right + WORD_MIN - g.minx)
            else:
                x = prev_x + off2(prev, g)
            right = x + g.maxx if space or prev is None else max(right, x + g.maxx)
            line.append(_place(g, x))
            prev, prev_x = g, x
            i += 1
        space = False
    return line


def window_gaps(line, k=3):
    """Min true distance from each glyph to the next k glyphs (the neighbour-only check misses a_b)."""
    out = []
    for i, (ca, ga, _) in enumerate(line):
        for cb, gb, _ in line[i + 1:i + 1 + k]:
            out.append((ca, cb, float(ga.distance(gb))))
    return out


# --- rule B: word space = WORD ink-to-ink, measured only on the cap-line-to-baseline band ------

from beadjoint.geom import Rect

WORD_BAND = (-4.0, 10.0)
WORD_TRUE = 3.5     # true-distance floor across a word space


@lru_cache(maxsize=None)
def band_x(g):
    """Word-space edges (left, right): halfway between the ink edge inside WORD_BAND and the bbox
    edge, so overhangs outside the band (j hook, ogonek) count half; bbox if no ink in the band."""
    hit = g.geom.intersection(Rect(-50, WORD_BAND[0], 50, WORD_BAND[1]))
    b = g.geom.bounds if hit.is_empty else hit.bounds
    return (b[0] + g.minx) / 2, (b[2] + g.maxx) / 2


def _set_b(text, glyphs, figure_cells):
    line, prev, prev_x, space, i, right, word = [], None, 0.0, False, 0, -1e9, []
    while i < len(text):
        ch = text[i]
        if ch == " ":
            space, i = True, i + 1
            continue
        if space:
            word = [gm for _, gm, _ in line[start:]]
        j = i + 1
        if figure_cells and ch in FIGURES:
            while j < len(text) and text[j] in FIGURES:
                j += 1
        run = [glyphs[c] for c in text[i:j]]
        g0 = run[0]
        if prev is None:
            x0 = -g0.minx
        elif space:
            x0 = right + WORD - band_x(g0)[0]           # word space from the whole previous word
            x0 = _clear(word, g0, x0, WORD_TRUE)        # descender overhangs (ę j , j) keep apart
        else:
            x0 = prev_x + off2(prev, g0)
        if space or prev is None:
            start = len(line)
        cells = figure_cells and ch in FIGURES
        run0 = x0 - cell_origin(0, g0, CELL_F) if cells else x0
        for k, g in enumerate(run):
            x = run0 + cell_origin(k, g, CELL_F) if cells else x0
            r = x + band_x(g)[1]
            right = r if (k == 0 and (space or prev is None)) else max(right, r)
            line.append(_place(g, x))
            prev, prev_x = g, x
        space, i = False, j
    return line


def _clear(word, g, x, gap):
    """Smallest x' >= x with true distance >= gap between g at x' and the previous word's ink."""
    from shapely import affinity
    from shapely.ops import unary_union
    w = unary_union(word)
    d = lambda xx: w.distance(affinity.translate(g.geom, xx))
    if d(x) >= gap:
        return x
    lo, hi = x, x + 20.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if d(mid) < gap else (lo, mid)
    return hi


def kerned_b(text, glyphs=None):
    return _set_b(text, glyphs or full_p(), figure_cells=False)


def mixed_b(text, glyphs=None):
    return _set_b(text, glyphs or full_mixed(), figure_cells=True)
