"""Accent marks and composition (Latin-1, Latin Extended-A, Romanian comma-below letters).

A composite is base + marks. Marks above sit 2w clear of the base: their ink bottom is at
y = -2 over x-height letters and y = -6 over capitals and ascender letters (b d h k l t); marks
below start 2w under the baseline (y = 12). Cedilla and ogonek attach to the base's bottom stroke.
The mark shapes are drawn in their own coordinates and placed by their ink box.
"""
import unicodedata

from shapely import affinity

from .geom import BALL as B, D, DOT, Rect, S, So

ABOVE_LOW, ABOVE_HIGH, BELOW_TOP = -2.0, -6.0, 12.0
ASCENDER_LETTERS = set("bdhklt")

SHAPES = {
    "grave": S((0, 0, B), (2.2, 2.4, B)),
    "acute": S((0, 2.4, B), (2.2, 0, B)),
    "circumflex": S((0, 2.5, B), (2.5, 0), (5, 2.5, B)),
    "caron": S((0, 0, B), (2.5, 2.5), (5, 0, B)),
    "breve": S((0, 0, B), (0, 2.5, 2.4), (5, 2.5, 2.4), (5, 0, B)),   # r2: half circle (r 2.5 would zero the ends)
    "tilde": S((0, 2, B), (2, 0), (4, 2), (6, 0, B)),
    "macron": S((0, 0), (5, 0)),
    "dot": D((0, 0), DOT),
    "dieresis": D((0, 0), DOT) | D((5, 0), DOT),
    "ring": So((0, 0, 2), (4, 0, 2), (4, 4, 2), (0, 4, 2)),           # r2: a true circle, 2w hole
    "doubleacute": S((0, 2.4, B), (1.2, 0, B)) | S((4.5, 2.4, B), (5.7, 0, B)),
    "commaabove": S((0, 2.6, B), (0.8, 0, B)),          # turned comma (ģ)
    "commabelow": S((0.8, 0, B), (0, 2.6, B)),
}
COMBINING = {"0300": "grave", "0301": "acute", "0302": "circumflex", "0303": "tilde", "0304": "macron",
             "0306": "breve", "0307": "dot", "0308": "dieresis", "030A": "ring", "030B": "doubleacute",
             "030C": "caron", "0326": "commabelow", "0327": "cedilla", "0328": "ogonek"}
# Latvian and Romanian letters decomposed with a cedilla are drawn with a comma below
COMMA_FOR_CEDILLA = set("GKLNRgklnrTt")
# attachment x for cedilla / ogonek, per base (where the bottom stroke is)
CEDILLA_X = {"c": 3.5, "s": 3.5, "C": 3.5, "S": 3.5}
OGONEK_X = {"a": 6, "e": 4.5, "i": 1, "u": 6, "A": 6, "E": 5, "I": 5, "U": 5}
BELOW_X = {"r": 1.0}                 # r2: ŗ's comma under the stem, not under the arch


def place_above(mark, cx, bottom):
    x0, y0, x1, y1 = mark.bounds
    return affinity.translate(mark, cx - (x0 + x1) / 2, bottom - y1)


def place_below(mark, cx, top=BELOW_TOP):
    x0, y0, x1, y1 = mark.bounds
    return affinity.translate(mark, cx - (x0 + x1) / 2, top - y0)


def cedilla(ax):
    return S((ax, 9), (ax, 13), (ax - 2.5, 13, B))


def ogonek(ax):
    return S((ax, 9), (ax, 13), (ax + 2.5, 13, B))


def apostrophe(x):
    """Caron on ď ľ ť Ľ: a tick to the right of the ascender, top cut flat on the cap line."""
    return S((x, -4.5), (x - 0.6, -1.4, B)).intersection(Rect(-20, -4, 40, 20))


def apostrophe_after(g, gap=2.05):
    """The apostrophe slid in from the right until it is `gap` from the letter (r1: ľ Ľ sat too far out)."""
    x = g.bounds[2] + 6.0
    for _ in range(80):
        if g.distance(apostrophe(x - 0.1)) < gap:
            break
        x -= 0.1
    return apostrophe(x)


def decompose(ch):
    """(base char, [mark names]) for a precomposed Latin letter, or None."""
    d = unicodedata.decomposition(ch)
    if not d or d.startswith("<"):
        return None
    parts = d.split()
    base = chr(int(parts[0], 16))
    marks = []
    for p in parts[1:]:
        if p not in COMBINING:
            return None
        marks.append(COMBINING[p])
    inner = decompose(base)            # e.g. ǖ: fully decompose nested forms
    if inner:
        base, marks = inner[0], inner[1] + marks
    return base, marks


def compose(ch, base_char, marks, bases, anchors=None, caron_above=False):
    """Geometry of ch from base glyphs (dict char -> geometry); anchors override a base's mark x;
    caron_above draws ď ť with a real caron over the letter (the monospace cell has no room for the
    apostrophe form)."""
    b = base_char
    above = [m for m in marks if m not in ("cedilla", "ogonek", "commabelow")]
    if above and b == "i":
        b = "ı"
    if above and b == "j":
        b = "ȷ"
    g = bases[b]
    x0, y0, x1, y1 = g.bounds
    cx = (x0 + x1) / 2
    if b == "ı":
        cx = 1.0
    if b == "ȷ":
        cx = 4.0
    if anchors and b in anchors:
        cx = anchors[b]
    high = b.isupper() or b in ASCENDER_LETTERS
    for m in marks:
        if m == "caron" and b in "dt" and caron_above:
            g = g | place_above(SHAPES["caron"], cx, ABOVE_HIGH)
        elif m == "caron" and b in "dltL":
            g = g | apostrophe_after(g)
        elif m in ("cedilla", "commabelow") and b == "g":      # r2: ģ = g + U+0327: turned comma above
            g = g | place_above(SHAPES["commaabove"], cx, ABOVE_LOW)
        elif m == "cedilla" and b in COMMA_FOR_CEDILLA:
            g = g | place_below(SHAPES["commabelow"], BELOW_X.get(b, cx))
        elif m == "cedilla":
            g = g | cedilla(CEDILLA_X.get(b, cx))
        elif m == "ogonek":
            g = g | ogonek(OGONEK_X.get(b, x1 - 1))
        elif m == "commabelow":
            g = g | place_below(SHAPES["commabelow"], BELOW_X.get(b, cx))
        else:
            if b == "l" and m == "acute" and not (anchors and "l" in anchors):
                cx = 1.0                                         # over the stem (r2: anchors win in Mono)
            g = g | place_above(SHAPES[m], cx, ABOVE_HIGH if high else ABOVE_LOW)
    return g
