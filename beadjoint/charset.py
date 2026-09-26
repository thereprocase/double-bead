"""The complete Beadjoint character set: the spec's sets plus capitals, symbols, specials and
accented letters, assembled per set (P proportional, M monospace, T mixed with the tabular 1).

Coverage: ASCII, Latin-1 Supplement, Latin Extended-A, Ș ș Ț ț, ȷ, the spacing accents, and the
common general punctuation (dashes, curly quotes, dagger, bullet, ellipsis, per mille, primes,
minus, fraction slash, euro, trade mark).
"""
import unicodedata
from functools import lru_cache
from types import MappingProxyType

from . import glyphs as spec
from . import latin, marks
from .geom import D, DOT, finish

EXTRA = "–—‘’‚“”„†‡•…‰‹›⁄€™′″−ȘșȚțȷ" + "ˆˇ˘˙˚˛˜˝" + "Ω⅛⅜⅝⅞←↑→↓≤≥≈" + "ẀẁẂẃẄẅỲỳ₺ƒẞ≠⅓⅔"   # r5, r12
CHARS = ([chr(c) for c in range(0x21, 0x7F)] + [chr(c) for c in range(0xA1, 0x100) if c != 0xAD]
         + [chr(c) for c in range(0x100, 0x180)] + list(EXTRA))
ALIASES = {"\u00a0": " ", "\u00ad": "-", "\u2009": " ", "\u202f": " ", "\u2007": " ", "\u2008": " ",
           "\u2010": "-", "\u2011": "-", "\u03bc": "µ", "\u2300": "Ø", "\u2126": "Ω", "\u2015": "—"}   # r4: spaces, hyphens, mu, diameter; r12: bar
SPACING_MARKS = {"¨": "dieresis", "¯": "macron", "´": "acute", "ˆ": "circumflex", "ˇ": "caron", "˘": "breve",
                 "˙": "dot", "˚": "ring", "˜": "tilde", "˝": "doubleacute"}
MONO_MAX = 10.0                                    # ink width that fits a 12w cell with a 2w gap
# How Mono composes accents (full_m, and the finishing checks through finish_inputs): marks sit over the
# stems of Mono's ı ȷ l rather than their ink centres, and ď ť take a real caron (no room for the apostrophe)
MONO_COMPOSE = MappingProxyType({"anchors": MappingProxyType({"ı": 4.5, "ȷ": 6.0, "l": 4.5}), "caron_above": True})


def _standalone(name):
    return marks.place_above(marks.SHAPES[name], marks.SHAPES[name].bounds[2] / 2 + 1, marks.ABOVE_LOW) \
        if name != "dot" else D((1.5, -3.5), DOT)


def _extras():
    x = {c: _standalone(n) for c, n in SPACING_MARKS.items()}
    x.update(latin.extras())
    return x


def _assemble(base, anchors=None, caron_above=False):
    """Finish base glyphs, then build every composite from finished bases (finishing is idempotent).
    Returns (finished, inputs): every glyph finished, and the geometry finishing received for it."""
    inputs = dict(base)
    fin = {c: finish(g) for c, g in base.items()}
    for ch in CHARS:
        if ch in fin:
            continue
        dec = marks.decompose(ch)
        if dec is None:
            continue
        b, ms = dec
        inputs[ch] = marks.compose(ch, b, ms, fin, anchors, caron_above)
        fin[ch] = finish(inputs[ch])
    return fin, inputs


# Every builder from here to finish_inputs is cached, in layers: full_p reads _assembled_p, which holds
# the finished glyphs, so clearing full_p alone rebuilds nothing. cache_clear() clears them all, for a
# caller that patches finish or a constructor and wants the families rebuilt with it.

@lru_cache(maxsize=None)
def raw_p():
    """Proportional base geometry before finishing. The result is cached and shared, so it is read-only;
    copy it with dict() to change it."""
    p = spec._raw_p()
    cap = latin.capitals()
    sym = latin.symbols(p)
    base = {**p, **cap, **sym}
    base.update(latin.specials(p, cap, sym))
    base.update(_extras())
    base["1"] = spec._raw_one_tabular()          # r1: the flag-only 1 reads as 7; P uses the footed 1 too
    base["w"] = latin.square_w()                  # r12
    return MappingProxyType(base)


@lru_cache(maxsize=None)
def _assembled_p():
    return _assemble(raw_p())


@lru_cache(maxsize=None)
def _assembled_m():
    return _assemble(raw_m(), **MONO_COMPOSE)


@lru_cache(maxsize=None)
def _tabular_one():
    return spec._raw_one_tabular()


@lru_cache(maxsize=None)
def full_p():
    fin = _assembled_p()[0]
    missing = [c for c in CHARS if c not in fin]
    if missing:
        raise ValueError(f"no geometry for {''.join(missing)!r}")
    return {c: spec.Glyph(c, f"P:{c}", fin[c]) for c in CHARS}


@lru_cache(maxsize=None)
def full_mixed():
    t = dict(full_p())
    t["1"] = spec.Glyph("1", "T:1", finish(_tabular_one()))
    return t


@lru_cache(maxsize=None)
def raw_m():
    """Monospace base geometry before finishing: P's, with the spec's M set (already soft-filtered)
    over it, the narrowed forms of glyphs too wide for the cell, the shared w and the Mono-only glyphs.
    Read-only like raw_p()."""
    base = dict(raw_p())
    for c, g in spec.set_m().items():
        # The spec set's J " - . / are soft-filtered copies of glyphs._raw_extension, a duplicate of
        # latin's J and symbols that the tuner does not catalog; P's raw shapes keep Mono's identical
        # to the other families', so an edit to them reaches all three.
        if c not in spec.EXTENSION:
            base[c] = g.geom
    base.update(latin.mono_narrow())                 # r12
    base["w"] = latin.square_w()
    base.update(latin.mono_extras())
    return MappingProxyType(base)


@lru_cache(maxsize=None)
def full_m():
    """Monospace: the spec's M glyphs, M-based composites, and every other glyph that fits the cell."""
    fin = _assembled_m()[0]
    out = {}
    for c in CHARS:
        g = fin.get(c)
        if g is None:
            continue
        x0, _, x1, _ = g.bounds
        if x1 - x0 <= MONO_MAX + 1e-3:          # r6: W measured 10.0004 after rotate180
            out[c] = spec.Glyph(c, f"M:{c}", g)
    return out


@lru_cache(maxsize=None)
def finish_inputs():
    """The geometry finishing received for every glyph of each family, {"P" | "T" | "M": {char: geometry}}:
    base glyphs raw, composites as composed from the finished bases. verify.fused_pieces compares it with
    the finished glyphs. Read-only."""
    p, m = _assembled_p()[1], _assembled_m()[1]
    fams = {"P": {c: p[c] for c in full_p()}}
    fams["T"] = {**fams["P"], "1": _tabular_one()}
    fams["M"] = {c: m[c] for c in full_m()}
    return MappingProxyType({k: MappingProxyType(v) for k, v in fams.items()})


def cache_clear():
    """Clear every cache in this module, hidden layers included, so the next family build runs finishing
    and composition again. Found by attribute, so a cache added later is cleared too. The spec sets in
    glyphs (set_p, set_m, set_mixed; raw_m reads set_m) keep their own caches."""
    for f in list(globals().values()):
        if getattr(f, "__module__", None) == __name__ and callable(getattr(f, "cache_clear", None)):
            f.cache_clear()


def glyph_name(ch):
    from fontTools.agl import UV2AGL
    return UV2AGL.get(ord(ch), f"uni{ord(ch):04X}")


def category(ch):
    return unicodedata.category(ch)
