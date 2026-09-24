"""Font files (spec 1 and 10), for the full character set.

    Double bead     set P, kerned: side bearings from the n-n gap, pair kerns from off()
    Double bead Tab   the mixed setting: P glyphs, figures on 9w cells (1 -> 1ₜ), no kerning between
                    figures, every other pair kerned from off()
    Double bead Mono  set M on 12w cells, no kerning (glyphs wider than 10w are left out)

1w = 50 font units, UPM 1000, Y_font = (10 - y) * 50: baseline 0, x-height 500, capitals and
figures 700 (the OS/2 cap height, which is what Fusion's text Height sets), descender -200.
Line pitch 1400 units = 28w (typo and hhea metrics, USE_TYPO_METRICS; round 2: at 20w an accent or a
bracket on one line runs into the descenders of the line above); win metrics cover the tallest accent
and the lowest comma so nothing is clipped.

Kerning (spec 10, scaled up): an accented letter shares its base letter's side bearings and kerning
class on each side where its ink ends within 0.3w of the base's; class pairs are computed on the
base glyphs. Every actual pair is then checked for the 1.98w true-distance floor with the class
kern applied, and gets its own exception kern where a mark would collide. Word space: the space is
kerned against every glyph so the ink-to-ink gap across a space is WORD (Tab font: a figure after
a space starts its 9w cell at that edge). GPOS 'kern' carries all of it; a legacy 'kern' table
carries the ASCII pairs for programs that only read that (FreeType's FT_Get_Kerning, GDI).
"""
import numpy as np
import shapely
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables._k_e_r_n import KernTable_format_0
from shapely import affinity
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from . import marks
from .charset import ALIASES, full_m, full_mixed, full_p, glyph_name
from .glyphs import FIGURES, pieces
from .setting import CELL_F, CELL_M, WORD, off

UNITS = 50
VERSION = "1.200"
KERN_DROP = 0.1
LINE_MIN = 1.98
GAP_TRIGGER, GAP_TARGET = 2.0, 2.02      # exceptions: below the trigger, push to the target
SIDE_TOL = 0.3
ASCII = {chr(c) for c in range(0x21, 0x7F)}

DESCRIPTION = ("Two-bead FDM font: every stroke is exactly two extrusion widths (w). Fusion text Height "
               "= 14 x line width (cap height); em = 20 x line width.")


def inkgap(a, b):
    return off(a, b) - a.maxx + b.minx


def side_reps(glyphs):
    """(left_rep, right_rep): the glyph whose left / right side a glyph shares (its base letter
    when the ink ends within SIDE_TOL of the base's on that side, else itself)."""
    left, right = {}, {}
    for c, g in glyphs.items():
        left[c] = right[c] = c
        dec = marks.decompose(c)
        if not dec or dec[0] not in glyphs:
            continue
        b = glyphs[dec[0]]
        if abs(g.minx - b.minx) < SIDE_TOL:
            left[c] = dec[0]
        if abs(g.maxx - b.maxx) < SIDE_TOL:
            right[c] = dec[0]
    return left, right


BEARING_MIN = 1.0      # half the 2w floor: with no kerning at all, no two glyphs come closer than 2w


def metrics(glyphs, left, right, cells=None):
    """Side bearings (w): spec 10 from the n-n gap on each side's representative, never below 1w
    (a program that ignores kerning still keeps every pair 2w apart; kerning pulls overhangs like
    T, f, j, y in pair by pair, and marks that float above the x-height get sane advances). Figures
    in the Tab font sit on their 9w cells."""
    n = glyphs["n"]
    half = inkgap(n, n) / 2
    lsb, rsb = {}, {}
    for c, g in glyphs.items():
        if cells and c in FIGURES:
            lsb[c] = rsb[c] = (cells - g.width) / 2
            continue
        lsb[c] = max(inkgap(n, glyphs[left[c]]) - half, BEARING_MIN)
        rsb[c] = max(inkgap(glyphs[right[c]], n) - half, BEARING_MIN)
    return lsb, rsb, half


def kerning(glyphs, left, right, lsb, rsb, no_kern=lambda a, b: False):
    """Class pairs on representatives, then per-pair exceptions for the true-distance floor.
    Returns (class_pairs {(right_rep, left_rep): w}, exceptions {(a, b): w})."""
    reps_r = sorted(set(right.values()))
    reps_l = sorted(set(left.values()))
    classes = {}
    for ra in reps_r:
        for rb in reps_l:
            if no_kern(ra, rb):
                classes[(ra, rb)] = 0.0
            else:
                classes[(ra, rb)] = inkgap(glyphs[ra], glyphs[rb]) - rsb[ra] - lsb[rb]
    exceptions = {}
    chars = list(glyphs)
    simple = {c: glyphs[c].geom.simplify(0.003) for c in chars}
    for a in chars:
        ga = simple[a]
        todo, dxs = [], []
        for b in chars:
            if no_kern(a, b):
                continue
            k = classes[(right[a], left[b])]
            if abs(k) < KERN_DROP:
                k = 0.0                                      # small class kerns are dropped (spec 10)
            # b's glyph-coordinate shift relative to a's, with the advance and kern rounded to font
            # units exactly as the TTF stores them (spec 10: ink(b) = ink(a) + rsb + k + lsb)
            adv = round((lsb[a] + glyphs[a].width + rsb[a]) * UNITS) / UNITS
            dx = adv + round(k * UNITS) / UNITS + (lsb[b] - glyphs[b].minx) - (lsb[a] - glyphs[a].minx)
            if glyphs[b].minx + dx - glyphs[a].maxx < GAP_TRIGGER:  # bbox gap under the floor: measure
                todo.append(b)
                dxs.append(dx)
        if not todo:
            continue
        moved = [affinity.translate(simple[b], dx) for b, dx in zip(todo, dxs)]
        dist = shapely.distance(np.array([ga] * len(moved), dtype=object), np.array(moved, dtype=object))
        for b, dx, d in zip(todo, dxs, dist):
            if d < GAP_TRIGGER:                             # margin over 1.98 for outline rounding
                extra = 0.0
                while d < GAP_TARGET:
                    extra += (GAP_TARGET - d) + 1e-4
                    d = ga.distance(affinity.translate(simple[b], dx + extra))
                k = classes[(right[a], left[b])]
                exceptions[(a, b)] = round(((k if abs(k) >= KERN_DROP else 0.0) + extra) * UNITS + 0.49) / UNITS
    return classes, exceptions


def _draw(geom, dx):
    """TrueType contours for geom shifted by dx (w): clockwise outers, counter-clockwise holes."""
    pen = TTGlyphPen(None)
    for p in pieces(geom):
        p = affinity.affine_transform(p, [UNITS, 0, 0, -UNITS, dx * UNITS, 10 * UNITS])
        p = p.simplify(0.2, preserve_topology=True)
        rings = []
        for ring in [p.exterior, *p.interiors]:
            pts = []
            for x, y in ring.coords[:-1]:
                q = (round(x), round(y))
                if not pts or q != pts[-1]:
                    pts.append(q)
            if len(pts) > 1 and pts[0] == pts[-1]:
                pts.pop()
            rings.append(pts)
        q = orient(Polygon(rings[0], rings[1:]), sign=-1.0)
        if not q.is_valid:
            q = q.buffer(0)
            if not q.is_valid or q.geom_type != "Polygon":
                raise ValueError("rounded outline is invalid")
            q = orient(q, sign=-1.0)
        for ring in [q.exterior, *q.interiors]:
            coords = list(ring.coords)[:-1]
            pen.moveTo(coords[0])
            for pt in coords[1:]:
                pen.lineTo(pt)
            pen.closePath()
    return pen.glyph()


def _fea(names, classes, left, right, pairs):
    """Feature text: one kern lookup, glyph pairs (exceptions, space) first, then class pairs."""
    def members(reps, rep):
        return sorted(names[c] for c, r in reps.items() if r == rep)
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;"]
    rr = sorted(set(right.values()))
    ll = sorted(set(left.values()))
    for i, r in enumerate(rr):
        lines.append(f"@KL{i} = [{' '.join(members(right, r))}];")
    for j, r in enumerate(ll):
        lines.append(f"@KR{j} = [{' '.join(members(left, r))}];")
    lines.append("lookup KERN {")
    for (a, b), v in sorted(pairs.items()):
        u = round(v * UNITS)
        if u:
            lines.append(f"  pos {names[a]} {names[b]} {u};")
    ri = {r: i for i, r in enumerate(rr)}
    lj = {r: j for j, r in enumerate(ll)}
    for (a, b), v in sorted(classes.items()):
        u = round(v * UNITS)
        if abs(v) >= KERN_DROP and u:
            lines.append(f"  pos @KL{ri[a]} @KR{lj[b]} {u};")
    lines += ["} KERN;", "feature kern { lookup KERN; } kern;"]
    return "\n".join(lines) + "\n"


def build_font(path, family, glyphs, lsb, rsb, space, fea=None, legacy=None, mono=False):
    names = {c: glyph_name(c) for c in glyphs}
    order = [".notdef", "space", "uni2007", "uni2008"] + [names[c] for c in glyphs]
    if len(set(order)) != len(order):
        raise ValueError("duplicate glyph names")
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(" "): "space", **{ord(c): names[c] for c in glyphs}}
    for a, c in ALIASES.items():                     # r4: pasted variants; r12: one list, charset.ALIASES
        if c == " ":
            cmap[ord(a)] = "space"
        elif c in glyphs:
            cmap[ord(a)] = names[c]
    cmap[0x2007], cmap[0x2008] = "uni2007", "uni2008"                  # figure space, punctuation space
    fb.setupCharacterMap(cmap)
    outlines, hm = {}, {}
    notdef = TTGlyphPen(None)
    for ring in ([(50, 0), (50, 700), (450, 700), (450, 0)], [(100, 50), (400, 50), (400, 650), (100, 650)]):
        notdef.moveTo(ring[0])
        for pt in ring[1:]:
            notdef.lineTo(pt)
        notdef.closePath()
    outlines[".notdef"], hm[".notdef"] = notdef.glyph(), (500, 50)
    outlines["space"], hm["space"] = TTGlyphPen(None).glyph(), (round(space * UNITS), 0)
    for gname, c in (("uni2007", "0"), ("uni2008", ".")):
        outlines[gname], hm[gname] = TTGlyphPen(None).glyph(), (round((lsb[c] + glyphs[c].width + rsb[c]) * UNITS), 0)
    lo, hi = 0.0, 0.0
    for c, g in glyphs.items():
        outlines[names[c]] = _draw(g.geom, lsb[c] - g.minx)
        hm[names[c]] = (round((lsb[c] + g.width + rsb[c]) * UNITS), round(lsb[c] * UNITS))
        lo, hi = min(lo, g.geom.bounds[1]), max(hi, g.geom.bounds[3])
    fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics(hm)
    win_asc, win_desc = round((10 - lo) * UNITS) + 20, round((hi - 10) * UNITS) + 20
    fb.setupHorizontalHeader(ascent=800, descent=-200, lineGap=400)     # r2: 28 w pitch keeps accents off the line above
    ps = "".join(w[:1].upper() + w[1:] for w in family.split()) + "-Regular"      # DoubleBeadTab-Regular
    fb.setupNameTable({"familyName": family, "styleName": "Regular", "uniqueFontIdentifier": f"{family} {VERSION}",
                       "fullName": family, "psName": ps, "version": f"Version {VERSION}", "description": DESCRIPTION})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, sTypoLineGap=400, usWinAscent=win_asc, usWinDescent=win_desc,
                sxHeight=500, sCapHeight=700, usWeightClass=400, achVendID="RPRO", fsSelection=0x40 | 0x80)
    fb.setupPost(isFixedPitch=1 if mono else 0)
    if fea:
        addOpenTypeFeaturesFromString(fb.font, fea)
    if legacy:
        kern = newTable("kern")
        kern.version = 0
        st = KernTable_format_0()
        st.coverage = 1
        st.tupleIndex = None
        nm = {**names, " ": "space"}
        st.kernTable = {(nm[a], nm[b]): round(v * UNITS) for (a, b), v in legacy.items() if round(v * UNITS)}
        kern.kernTables = [st]
        fb.font["kern"] = kern
    os2 = fb.font["OS/2"]                             # r12: Windows reads code page support from these bits
    os2.recalcUnicodeRanges(fb.font)
    os2.recalcCodePageRanges(fb.font)
    fb.save(str(path))
    return {"glyphs": len(glyphs), "win": [win_asc, win_desc]}


def _space_pairs(glyphs, lsb, rsb, half, cells=None):
    """Kerns against the space (advance WORD - 2*half) so the gap across a space is WORD between the
    word-space edges (setting._edges: descender overhangs count half), as the setting engine does.
    The engine's whole-previous-word edge and 3.5w floor cannot be expressed as pair kerns."""
    from .setting import _edges
    pairs = {}
    for c, g in glyphs.items():
        el, er = _edges(g)
        pairs[(c, " ")] = half - rsb[c] - (g.maxx - er)
        pairs[(" ", c)] = half - lsb[c] - (el - g.minx)
    return pairs


def _legacy(glyphs, classes, exceptions, left, right, space_pairs, no_kern):
    """ASCII pairs (and the space) for the legacy table, same values as GPOS."""
    out = {}
    for a in glyphs:
        if a not in ASCII:
            continue
        for b in glyphs:
            if b not in ASCII or no_kern(a, b):
                continue
            if (a, b) in exceptions:
                out[(a, b)] = exceptions[(a, b)]
            else:
                v = classes[(right[a], left[b])]
                if abs(v) >= KERN_DROP:
                    out[(a, b)] = v
    for (a, b), v in space_pairs.items():
        if a in ASCII or b in ASCII:
            out[(a, b)] = v
    return out


def build_all(out_dir, log=print):
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for family, fname, glyphs, cells in (("Double bead", "DoubleBead-Regular.ttf", full_p(), None),
                                         ("Double bead Tab", "DoubleBeadTab-Regular.ttf", full_mixed(), CELL_F)):
        left, right = side_reps(glyphs)
        lsb, rsb, half = metrics(glyphs, left, right, cells)
        no_kern = (lambda a, b: a in FIGURES and b in FIGURES) if cells else (lambda a, b: False)
        classes, exceptions = kerning(glyphs, left, right, lsb, rsb, no_kern)
        space = WORD - 2 * half
        sp = _space_pairs(glyphs, lsb, rsb, half, cells)
        names = {c: glyph_name(c) for c in glyphs}
        names[" "] = "space"
        fea = _fea(names, classes, left, right, {**sp, **exceptions})
        legacy = _legacy(glyphs, classes, exceptions, left, right, sp, no_kern)
        r = build_font(out_dir / fname, family, glyphs, lsb, rsb, space, fea=fea, legacy=legacy)
        r.update({"class_pairs": sum(1 for v in classes.values() if abs(v) >= KERN_DROP), "exceptions": len(exceptions),
                  "classes": [len(set(right.values())), len(set(left.values()))], "legacy_pairs": len(legacy),
                  "space_w": round(space, 3)})
        report[family] = r
        log(family, r)
    m = full_m()
    lsb = {c: (CELL_M - g.width) / 2 for c, g in m.items()}
    report["Double bead Mono"] = build_font(out_dir / "DoubleBeadMono-Regular.ttf", "Double bead Mono", m, lsb, lsb, CELL_M, mono=True)
    return report
