"""Beadjoint glyphs: set P (proportional, spec 7), set M (monospace, spec 8), the tabular one,
and the extension glyphs the masonry-key labels need (spec 12 rules: capitals and tall marks on
the figure height y in [-4, 10], bars on the 2-4-2-4-2 band stack, checked like every glyph).

Every constructor below is hand-transcribed from docs/SPEC.md; the notation maps as
    S[(1,1)●, (6,1)^0, ...]   ->  S((1, 1, B), (6, 1, 0), ...)
    S°[...]                   ->  So(...)
The finishing filter soft() is applied to every glyph of every set.
"""
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from shapely.geometry import MultiPolygon

from .geom import BALL as B, D, Rect, S, So, rotate180, soft, solve, widen

FIGURES = "0123456789"
LOWER = "abcdefghijklmnopqrstuvwxyz"
EXTENSION = 'J/"-.'
TALL = set(FIGURES) | set('J/"')     # pairs touching these use the figure band [-4, 10]


@dataclass(frozen=True, eq=False)     # identity hash: glyphs are cached singletons
class Glyph:
    char: str
    key: str          # unique id, e.g. "P:a", "M:0", "T:1"
    geom: object      # shapely (Multi)Polygon, w units, y down

    @property
    def bounds(self):
        return self.geom.bounds

    @property
    def minx(self):
        return self.geom.bounds[0]

    @property
    def maxx(self):
        return self.geom.bounds[2]

    @property
    def width(self):
        b = self.geom.bounds
        return b[2] - b[0]

    @property
    def figure(self):
        return self.char in FIGURES

    @property
    def tall(self):
        """Pairs touching a tall glyph use the figure band [-4, 10] for optical spacing: figures,
        capitals, and symbols that reach above the x-height; lowercase letters (marks included) never."""
        c = self.char
        if c in TALL:
            return True
        cat = unicodedata.category(c)
        if cat == "Lu":
            return True
        if cat.startswith("L"):
            return False
        return self.geom.bounds[1] < -1.5


def _raw_p():
    g = {}
    g["a"] = S((1, 1, B), (6, 1), (6, 10)) | S((6, 5), (1, 5), (1, 9), (6, 9))
    g["b"] = S((1, -4), (1, 10)) | S((1, 1), (6, 1), (6, 9), (1, 9))
    g["c"] = S((6, 1, B), (1, 1), (1, 9), (6, 9, B))
    g["d"] = S((6, -4), (6, 10)) | S((6, 1), (1, 1), (1, 9), (6, 9))
    g["e"] = S((1, 5), (6, 5), (6, 1), (1, 1), (1, 9), (6, 9, B))
    g["f"] = S((2.5, 10), (2.5, -3), (5.5, -3, B)) | S((0, 1), (6, 1))
    g["g"] = S((6, 0), (6, 13), (1, 13, B)) | S((6, 1), (1, 1), (1, 9), (6, 9))
    g["h"] = S((1, -4), (1, 10)) | S((1, 1), (6, 1), (6, 10))
    g["i"] = S((1, 0), (1, 10)) | D((1, -3))
    g["j"] = S((4, 0), (4, 13), (1, 13, B)) | D((4, -3))
    g["k"] = S((1, -4), (1, 10)) | S((6, 1, B), (2.5, 6), (6.5, 9, B))
    g["l"] = S((1, -4), (1, 9), (3, 9, B))
    g["m"] = S((1, 10), (1, 1, 0), (9, 1), (9, 10)) | S((5, 1), (5, 10))
    g["n"] = S((1, 10), (1, 1, 0), (6, 1), (6, 10))
    g["o"] = So((1, 1), (6, 1), (6, 9), (1, 9))
    g["p"] = S((1, 0), (1, 14)) | S((1, 1), (6, 1), (6, 9), (1, 9))
    g["q"] = S((6, 0), (6, 14)) | S((6, 1), (1, 1), (1, 9), (6, 9))
    g["r"] = S((1, 10), (1, 1, 0), (6, 1), (6, 3, B))
    g["s"] = S((6, 1, B), (1, 1), (1, 5), (6, 5), (6, 9), (1, 9, B))
    g["t"] = S((2.5, -3), (2.5, 9), (5.5, 9, B)) | S((0, 1), (6, 1))
    g["u"] = S((1, 0), (1, 9), (6, 9)) | S((6, 0), (6, 10))
    g["v"] = solve(lambda vy: S((1, 1, B), (4, vy), (7, 1, B)))
    g["w"] = solve(lambda vy: S((1, 1, B), (3.125, vy), (5.25, 3.5), (7.375, vy), (9.5, 1, B)))
    g["x"] = S((1, 1, B), (7, 9, B)) | S((7, 1, B), (1, 9, B))
    g["y"] = S((7, 1, B), (2.2, 13, B)) | S((0.8, 1, B), (4.6, 7))
    g["z"] = S((0, 1), (6.3, 1, 0.8), (0.7, 9, 0.8), (7, 9))

    g["0"] = So((1, -3), (6, -3), (6, 9), (1, 9))
    g["1"] = S((1, -3, B), (4, -3), (4, 10))
    g["2"] = S((1, -3, B), (6, -3), (6, 3), (1, 3), (1, 9, 0), (7, 9))
    g["3"] = S((1, -3, B), (6, -3), (6, 9), (1, 9, B)) | S((2, 3, B), (6, 3))
    g["4"] = S((1, -4), (1, 3), (6, 3)) | S((6, -4), (6, 10))
    g["5"] = S((7, -3), (1, -3, 0), (1, 3, 0), (6, 3), (6, 9), (1, 9, B))
    g["6"] = S((6, -3, B), (1, -3), (1, 9), (6, 9), (6, 3), (1, 3))
    g["7"] = S((0, -3), (6.4, -3, 2), (3.4, 9, B))
    g["8"] = So((1, -3), (6, -3), (6, 9), (1, 9)) | S((1, 3), (6, 3))
    g["9"] = rotate180(g["6"], (3.5, 3))
    return g


WIDENED = "abcdeghnopqsu02345689"      # spec 8: M[c] = widen(P[c])


def _raw_m_rebuilt():
    g = {}
    g["i"] = S((2, 1, B), (4.5, 1, 0), (4.5, 9)) | S((1, 9), (8, 9)) | D((4.5, -3))
    g["l"] = S((2, -3, B), (4.5, -3, 0), (4.5, 9), (8, 9, B))
    g["j"] = S((3, 1, B), (6, 1, 0), (6, 13), (1, 13, B)) | D((6, -3))
    g["f"] = S((3.5, 10), (3.5, -3), (8, -3, B)) | S((0.5, 1), (8.5, 1))
    g["t"] = S((3.5, -3), (3.5, 9), (8, 9, B)) | S((0.5, 1), (8.5, 1))
    g["r"] = S((2.5, 10), (2.5, 1, 0), (8, 1), (8, 3, B)) | S((0.5, 9), (5.5, 9))
    g["k"] = S((1, -4), (1, 10)) | S((8, 1, B), (2.5, 6), (8.5, 9, B))
    g["v"] = solve(lambda vy: S((1, 1, B), (4.5, vy), (8, 1, B)))
    g["w"] = solve(lambda vy: S((1, 1, B), (3, vy, 0.9), (5, 3.5, 0.9), (7, vy, 0.9), (9, 1, B)))
    g["x"] = S((1, 1, B), (8, 9, B)) | S((8, 1, B), (1, 9, B))
    g["y"] = S((8, 1, B), (2.6, 13, B)) | S((0.8, 1, B), (5.2, 7))
    g["z"] = S((0, 1), (8.3, 1, 0.8), (0.7, 9, 0.8), (9, 9))
    g["1"] = S((1.5, -3, B), (4.5, -3), (4.5, 9)) | S((1, 9), (8, 9))
    g["7"] = S((0, -3), (8.4, -3, 2), (4.6, 9, B))
    g["0"] = So((1, -3), (7, -3), (7, 9), (1, 9))     # Beadjoint r6: 8w, so Mono's 0 is not its 9w O
    return g


def _raw_one_tabular():
    """1ₜ: the tabular 1 of the mixed setting, fits the 9w figure cell."""
    return S((1, -3, B), (3.5, -3), (3.5, 9)) | S((0.5, 9), (6.5, 9))


SLASH_RUN = 4.0      # horizontal run of the slash centreline over the 14w figure height


def _slash():
    """Figure-height solidus: a 2w diagonal (measured perpendicular, R8) cut flat on the guides."""
    rise = 14.0
    half = (rise ** 2 + SLASH_RUN ** 2) ** 0.5 / rise       # horizontal half-thickness
    k = SLASH_RUN / rise                                     # x shift per unit of rise
    line = S((half - k, 11), (half + SLASH_RUN + k, -5))     # 1w past each guide, then cut
    return line.intersection(Rect(-5, -4, 20, 10))


def _raw_extension():
    """Glyphs outside the spec's sets, built to its rules (spec 12) for the masonry labels."""
    e = {}
    e["J"] = S((6, -4), (6, 9), (1, 9), (1, 6, B))          # stem flat on the cap line, hook with ball
    e["/"] = _slash()
    e['"'] = S((1, -4), (1, -1, B)) | S((5, -4), (5, -1, B))  # inch mark: 2w ticks, 2w apart
    e["-"] = S((1, 3, B), (4, 3, B))                          # on the figures' middle band [2, 4]
    e["."] = D((1, 9))
    return e


def _finish(raw, prefix):
    return {c: Glyph(c, f"{prefix}:{c}", soft(g)) for c, g in raw.items()}


@lru_cache(maxsize=None)
def set_p():
    """Proportional set P plus the extension glyphs."""
    raw = _raw_p()
    raw.update(_raw_extension())
    return _finish(raw, "P")


@lru_cache(maxsize=None)
def set_m():
    """Monospace set M: widened P glyphs, m as in P, the rebuilt ones, extension glyphs as in P."""
    p = set_p()
    m = {c: Glyph(c, f"M:{c}", soft(widen(p[c].geom))) for c in WIDENED}
    m["m"] = Glyph("m", "M:m", p["m"].geom)
    m.update(_finish(_raw_m_rebuilt(), "M"))
    for c in EXTENSION:
        m[c] = Glyph(c, f"M:{c}", p[c].geom)
    return m


@lru_cache(maxsize=None)
def set_mixed():
    """Letters and figures from P, with 1 -> 1ₜ (the mixed setting's glyphs)."""
    t = dict(set_p())
    t["1"] = Glyph("1", "T:1", soft(_raw_one_tabular()))
    return t


def pieces(g):
    return list(g.geoms) if isinstance(g, MultiPolygon) else [g]
