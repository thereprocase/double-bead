"""The complete Beadjoint character set: the spec's sets plus capitals, symbols, specials and
accented letters, assembled per set (P proportional, M monospace, T mixed with the tabular 1).

Coverage: ASCII, Latin-1 Supplement, Latin Extended-A, Ș ș Ț ț, ȷ, the spacing accents, and the
common general punctuation (dashes, curly quotes, dagger, bullet, ellipsis, per mille, primes,
minus, fraction slash, euro, trade mark).
"""
import unicodedata
from functools import lru_cache

from shapely import affinity

from . import glyphs as spec
from . import latin, marks
from .geom import BALL as B, D, DOT, S, finish

EXTRA = "–—‘’‚“”„†‡•…‰‹›⁄€™′″−ȘșȚțȷ" + "ˆˇ˘˙˚˛˜˝" + "Ω⅛⅜⅝⅞←↑→↓≤≥≈" + "ẀẁẂẃẄẅỲỳ₺ƒẞ≠⅓⅔"   # r5, r12
CHARS = ([chr(c) for c in range(0x21, 0x7F)] + [chr(c) for c in range(0xA1, 0x100) if c != 0xAD]
         + [chr(c) for c in range(0x100, 0x180)] + list(EXTRA))
ALIASES = {"\u00a0": " ", "\u00ad": "-", "\u2009": " ", "\u202f": " ", "\u2007": " ", "\u2008": " ",
           "\u2010": "-", "\u2011": "-", "\u03bc": "µ", "\u2300": "Ø", "\u2126": "Ω", "\u2015": "—"}   # r4: spaces, hyphens, mu, diameter; r12: bar
SPACING_MARKS = {"¨": "dieresis", "¯": "macron", "´": "acute", "ˆ": "circumflex", "ˇ": "caron", "˘": "breve",
                 "˙": "dot", "˚": "ring", "˜": "tilde", "˝": "doubleacute"}
MONO_MAX = 10.0                                    # ink width that fits a 12w cell with a 2w gap


def _standalone(name):
    return marks.place_above(marks.SHAPES[name], marks.SHAPES[name].bounds[2] / 2 + 1, marks.ABOVE_LOW) \
        if name != "dot" else D((1.5, -3.5), DOT)


def _extras():
    x = {c: _standalone(n) for c, n in SPACING_MARKS.items()}
    x["¸"] = S((3, 11), (3, 13), (1, 13, B))
    x["˛"] = S((1, 11), (1, 13), (3.5, 13, B))
    x["ŉ"] = D((1.7, -2.6), 1.4) | S((1.7, -2.6), (0.7, 0.4, B)) | latin.shift(spec._raw_p()["n"], 4.4)
    return x


def _assemble(base, anchors=None, caron_above=False):
    """Finish base glyphs, then build every composite from finished bases (finishing is idempotent)."""
    fin = {c: finish(g) for c, g in base.items()}
    for ch in CHARS:
        if ch in fin:
            continue
        dec = marks.decompose(ch)
        if dec is None:
            continue
        b, ms = dec
        fin[ch] = finish(marks.compose(ch, b, ms, fin, anchors, caron_above))
    return fin


@lru_cache(maxsize=None)
def raw_p():
    p = spec._raw_p()
    cap = latin.capitals()
    sym = latin.symbols(p)
    base = {**p, **cap, **sym}
    base.update(latin.specials(p, cap, sym))
    base.update(_extras())
    base["1"] = spec._raw_one_tabular()          # r1: the flag-only 1 reads as 7; P uses the footed 1 too
    base["w"] = latin.square_w()                  # r12
    return base


@lru_cache(maxsize=None)
def full_p():
    fin = _assemble(raw_p())
    missing = [c for c in CHARS if c not in fin]
    if missing:
        raise ValueError(f"no geometry for {''.join(missing)!r}")
    return {c: spec.Glyph(c, f"P:{c}", fin[c]) for c in CHARS}


@lru_cache(maxsize=None)
def full_mixed():
    t = dict(full_p())
    t["1"] = spec.Glyph("1", "T:1", finish(spec._raw_one_tabular()))
    return t


@lru_cache(maxsize=None)
def full_m():
    """Monospace: the spec's M glyphs, M-based composites, and every other glyph that fits the cell."""
    m_spec = spec.set_m()
    base = {c: g for c, g in raw_p().items()}
    for c, g in m_spec.items():
        base[c] = g.geom
    base.update(latin.mono_narrow())                 # r12
    base["w"] = latin.square_w()
    base["ı"] = S((2, 1, B), (4.5, 1, 0), (4.5, 9)) | S((1, 9), (8, 9))
    base["ȷ"] = S((3, 1, B), (6, 1, 0), (6, 13), (1, 13, B))
    # Three DOT-size dots with 2w gaps need 13w of ink, past the 10w cell; mono keeps 2w dots here.
    base["…"] = D((1, 9)) | D((5, 9)) | D((9, 9))
    fin = _assemble(base, anchors={"ı": 4.5, "ȷ": 6.0, "l": 4.5}, caron_above=True)
    out = {}
    for c in CHARS:
        g = fin.get(c)
        if g is None:
            continue
        x0, _, x1, _ = g.bounds
        if x1 - x0 <= MONO_MAX + 1e-3:          # r6: W measured 10.0004 after rotate180
            out[c] = spec.Glyph(c, f"M:{c}", g)
    return out


def glyph_name(ch):
    from fontTools.agl import UV2AGL
    return UV2AGL.get(ord(ch), f"uni{ord(ch):04X}")


def category(ch):
    return unicodedata.category(ch)
