"""Frodo r4 prototypes of setting changes (the package is not edited; these wrap it).

    kerned_r4 / mixed_r4  - runs of spaces count (n spaces = WORD + (n-1) * the TTF's space advance, as
                            the fonts render them); U+00A0 is a space (the fonts map it so); an optional
                            uniform tracking added to every pair inside a word
    missing(text)         - the characters a set would reject, with a readable message
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import beadjoint.setting as st
from beadjoint.charset import full_mixed, full_p
from beadjoint.glyphs import FIGURES

SPACES = {" ", "\u00a0"}


def space_advance(glyphs):
    """The fonts' space advance: WORD - the n-n ink gap (fontfile.build_all: space = WORD - 2 * half)."""
    n = glyphs["n"]
    return st.WORD - (st.off(n, n) - n.maxx + n.minx)


def missing(text, glyphs=None):
    glyphs = glyphs or full_p()
    bad = sorted({c for c in text if c not in glyphs and c not in SPACES})
    if bad:
        return "Beadjoint has no glyph for " + ", ".join(f"{c!r} (U+{ord(c):04X})" for c in bad)
    return None


def kerned_r4(text, glyphs=None, track=0.0):
    glyphs = glyphs or full_p()
    err = missing(text, glyphs)
    if err:
        raise ValueError(err)
    adv = space_advance(glyphs)
    line, prev, prev_x, spaces, word = [], None, 0.0, 0, []
    for ch in text:
        if ch in SPACES:
            spaces += 1
            continue
        g = glyphs[ch]
        if prev is None:
            x = -g.minx                    # leading spaces are dropped, as before
        elif spaces:
            x = st._word_start(word, g) + (spaces - 1) * adv
            word = []
        else:
            x = prev_x + st.off(prev, g) + track
        line.append(st._place(g, x))
        word.append((g, x))
        prev, prev_x, spaces = g, x, 0
    return line


def mixed_r4(text, glyphs=None, track=0.0):
    """mixed() with runs of spaces counted and NBSP as a space; figures stay on their 9w cells."""
    glyphs = glyphs or full_mixed()
    err = missing(text, glyphs)
    if err:
        raise ValueError(err)
    adv = space_advance(glyphs)
    line, prev, prev_x, spaces, i, word = [], None, 0.0, 0, 0, []
    while i < len(text):
        ch = text[i]
        if ch in SPACES:
            spaces, i = spaces + 1, i + 1
            continue
        extra = max(0, spaces - 1) * adv
        if ch in FIGURES:
            j = i
            while j < len(text) and text[j] in FIGURES:
                j += 1
            run = [glyphs[c] for c in text[i:j]]
            c0 = st.cell_origin(0, run[0], st.CELL_F)
            if prev is None:
                run0 = 0.0
            elif spaces:
                run0 = st._word_start(word, run[0]) + extra - c0
                word = []
            else:
                run0 = prev_x + st.off(prev, run[0]) + track - c0
            for k, g in enumerate(run):
                x = run0 + st.cell_origin(k, g, st.CELL_F)
                line.append(st._place(g, x))
                word.append((g, x))
                prev, prev_x = g, x
            i = j
        else:
            g = glyphs[ch]
            if prev is None:
                x = -g.minx
            elif spaces:
                x = st._word_start(word, g) + extra
                word = []
            else:
                x = prev_x + st.off(prev, g) + track
            line.append(st._place(g, x))
            word.append((g, x))
            prev, prev_x = g, x
            i += 1
        spaces = 0
    return line
