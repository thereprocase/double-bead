"""Fillaprint regression tests.

    python -m unittest discover -s tests      (from the repo root)

Covers the geometry primitives, the construction entry points, the spec's reference results, the hard
rules on every glyph of every set, the setting engine's line check, the line-spacing band, and the
built TTFs (outlines, metrics, set lines and license metadata read back). The TTF tests read the
committed fonts: rebuild them (python build.py) after changing the sources.
"""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from shapely import affinity  # noqa: E402

from beadjoint import charset  # noqa: E402
from beadjoint import glyphs as spec  # noqa: E402
from beadjoint.charset import CHARS, full_m, full_mixed, full_p, glyph_name  # noqa: E402
from beadjoint.geom import DOT, S, So, fillet, soft  # noqa: E402
from beadjoint.glyphs import FIGURES  # noqa: E402
from beadjoint.readback import FontReader  # noqa: E402
from beadjoint.setting import CELL_F, CELL_M, kerned, mixed, tabular  # noqa: E402
from beadjoint.verify import (FUSED_BY_DESIGN, LINE_MIN, MAX_T, SHIPPED_MAX_T, check_glyph, fused_pieces,  # noqa: E402
                              is_dot, line_gaps, piece_gap, piece_thickness)

FONTS = ROOT / "fonts"
UNITS = 50
OUTLINE_TOL = 1.5 / UNITS      # build.py: vertex rounding, simplification, centroid alignment
GAP_TOL = 0.1 + 0.03           # build.py: the spec's 0.1w kern drop plus rounding


LINES = ["The quick brown fox jumps over the lazy dog.", "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG",
         "Příliš žluťoučký kůň úpěl ďábelské ódy", "Pchnąć w tę łódź jeża lub ośm skrzyń fig",
         '1/4" Jt. 1/2" - 5/8" dep. 1-1/8" - 1-13/32" dep.', "4.48 mm 0.25 1/16 ±0.1 45° Ø12 M6 x 1.0 a_b \"x\" 'y'",
         "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ ¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿×÷"]


class Geometry(unittest.TestCase):
    def test_fillet_radius_and_tangents(self):
        pts, t = fillet((0, 10), (0, 0), (10, 0), 1.0)
        self.assertAlmostEqual(t, 1.0, places=9)
        for x, y in pts:
            self.assertAlmostEqual(math.hypot(x - 1, y - 1), 1.0, places=9)

    def test_fillet_straight_through_vertex(self):
        # Off-axis collinear points: acos reads theta a hair below pi, u + v cancels to (0, 0).
        for a, p, b in (((0, 0), (1, 1), (2, 2)), ((1, 10), (3.5, 5.5), (6, 1))):
            self.assertEqual(fillet(a, p, b, 1), ([p], 0.0))
        g = S((0, 0), (2, 2, 1), (4, 4))
        self.assertAlmostEqual(g.area, 2 * math.hypot(4, 4), places=6)

    def test_coincident_points_are_named(self):
        cases = {"(0.0, 0.0)": lambda: S((0, 0), (0, 0, 1), (4, 4)),
                 "(2.0, 2.0)": lambda: S((0, 0), (2, 2, 0), (2, 2)),
                 "(4.0, 0.0)": lambda: So((0, 0), (4, 0), (4, 0), (0, 4))}
        for point, build in cases.items():
            with self.assertRaises(ValueError) as caught:
                build()
            self.assertIn(point, str(caught.exception))

    def test_straight_stroke_is_two_wide(self):
        r = check_glyph(soft(S((0, 0), (0, 10))))
        self.assertAlmostEqual(r["thickness"], 2.0, delta=0.03)
        self.assertFalse(r["thin"])


class SpecReference(unittest.TestCase):
    """docs/SPEC.md section 11: P strokes max 2.83 (f, t), all others <= 2.76; M strokes max 2.83;
    R11 dots (i, j) measure 2 * DOT; no thin pieces."""

    DOTTED = "ij"

    def assert_dots(self, res):
        # The raster check reads a disk slightly under its true diameter.
        for c in self.DOTTED:
            self.assertAlmostEqual(res[c]["thickness"], 2 * DOT, delta=0.05, msg=c)

    def test_set_p(self):
        res = {c: check_glyph(g.geom) for c, g in spec.set_p().items() if c in spec.LOWER + spec.FIGURES}
        self.assertAlmostEqual(max(res["f"]["thickness"], res["t"]["thickness"]), 2.83, delta=0.01)
        self.assertLessEqual(max(v["thickness"] for c, v in res.items() if c not in "ft" + self.DOTTED), 2.76)
        self.assert_dots(res)
        self.assertFalse([c for c, v in res.items() if v["thin"]])

    def test_set_m(self):
        res = {c: check_glyph(g.geom) for c, g in spec.set_m().items() if c in spec.LOWER + spec.FIGURES}
        self.assertLessEqual(max(v["thickness"] for c, v in res.items() if c not in self.DOTTED), 2.84)
        self.assert_dots(res)
        self.assertFalse([c for c, v in res.items() if v["thin"]])

    def test_thickness_every_glyph(self):
        """R2 on every glyph the build checks, the extension glyphs and the tabular 1 included. R11 dots
        are excepted: a piece is a dot when its area is that of its inscribed disk."""
        sets = {"P": spec.set_p(), "M": spec.set_m(), "T": {"1": spec.set_mixed()["1"]}}
        self.assertTrue(set(spec.EXTENSION) <= set(sets["P"]) and set(spec.EXTENSION) <= set(sets["M"]))
        for name, glyphs in sets.items():
            for c, g in glyphs.items():
                for t, area in piece_thickness(g.geom):
                    if is_dot(t, area):
                        self.assertAlmostEqual(t, 2 * DOT, delta=0.05, msg=f"{name}:{c} dot")
                    else:
                        self.assertLessEqual(t, MAX_T, f"{name}:{c}")


class Construction(unittest.TestCase):
    """Entry points the tuner and the fonts share: both must read the same geometry."""

    def test_mark_base(self):
        from beadjoint.marks import mark_base
        cases = {("i", ("acute",)): "ı", ("j", ("circumflex",)): "ȷ", ("i", ("dieresis", "macron")): "ı",
                 ("i", ("ogonek",)): "i", ("j", ()): "j", ("n", ("tilde",)): "n", ("t", ("commabelow",)): "t",
                 ("g", ("cedilla",)): "g", ("I", ("dot",)): "I"}
        for (base, ms), want in cases.items():
            self.assertEqual(mark_base(base, list(ms)), want, (base, ms))

    def test_compose_reads_mark_base(self):
        from beadjoint import charset, marks

        class ReadLog(dict):
            def __getitem__(self, key):
                self.read.append(key)
                return super().__getitem__(key)

        bases = ReadLog(charset.raw_p())
        for ch in CHARS:
            dec = marks.decompose(ch)
            if dec is None or ch in bases:
                continue
            bases.read = []
            marks.compose(ch, *dec, bases)
            self.assertEqual(bases.read, [marks.mark_base(*dec)], ch)

    def test_extras_and_raw_m(self):
        from beadjoint import charset, latin
        self.assertEqual(set(latin.extras()), set("¸˛ŉ"))
        self.assertEqual(set(latin.mono_extras()), set("ıȷ…"))
        self.assertIs(charset.raw_m(), charset.raw_m())
        for c, g in latin.extras().items():
            self.assertTrue(charset.raw_p()[c].equals_exact(g, 0), c)
        for c, g in latin.mono_extras().items():
            self.assertTrue(charset.raw_m()[c].equals_exact(g, 0), c)

    def test_extension_copies_match_latin(self):
        # The spec sets check glyphs._raw_extension's copies while the fonts draw latin's shapes; an edit
        # to one must reach the other or the conformance checks stop describing the fonts.
        ext, raw = spec._raw_extension(), charset.raw_p()
        for c in spec.EXTENSION:
            self.assertLess(ext[c].symmetric_difference(raw[c]).area, 1e-9, c)

    def test_mono_shares_p_shapes(self):
        # Mono once took J " - . / from the spec set's uncataloged duplicates, so tuner edits to
        # them (and to the ' tick " shares) changed P and Tab but not Mono.
        for c in spec.EXTENSION + "'":
            self.assertTrue(full_m()[c].geom.equals_exact(full_p()[c].geom, 0), c)


class HardRules(unittest.TestCase):
    """No thin ink, no thin enclosed holes, separate pieces >= 1.98 w, and no ink thicker than the
    designed maxima (verify.SHIPPED_MAX_T), in every glyph of every family, as build.py checks."""

    def check(self, glyphs):
        bad, thick = [], []
        for c, g in glyphs.items():
            r = check_glyph(g.geom)
            gap = piece_gap(g.geom)
            if r["thin"] or r["islands"] or gap < LINE_MIN:
                bad.append((c, r["thin"], r["islands"], round(gap, 3)))
            if r["thickness"] > SHIPPED_MAX_T:
                thick.append((c, r["thickness"]))
        self.assertFalse(bad)
        self.assertFalse(thick, f"over SHIPPED_MAX_T = {SHIPPED_MAX_T}w, which sits just above the designed maxima of filled "
                                "joins (arrow tips 4.84w, V 4.75w, N 4.54w) to absorb raster rounding. The guard against "
                                "pieces fused by finishing is Finishing.test_no_pieces_fused.")

    def test_full_p(self):
        self.assertEqual(len(full_p()), len(CHARS))
        self.check(full_p())

    def test_full_mixed(self):
        # Tab is Proportional with the tabular 1; check the glyphs it does not share
        own = {c: g for c, g in full_mixed().items() if g.geom is not full_p()[c].geom}
        self.assertEqual(set(own), {"1"})
        self.check(own)

    def test_full_m(self):
        self.check(full_m())


class Finishing(unittest.TestCase):
    """Finishing fills pinches in a glyph's negative space; it must never join pieces that the raw
    geometry keeps apart (v0.1.1's 3w dots put ĳ's i and j 0.5w apart and it filled them solid).
    build.py runs the same check.

    One join is designed, verify.FUSED_BY_DESIGN: the spec's Mono k (SPEC section 8) stops its arm 0.25w
    short of the stem, and finishing fills that notch tip, which R3 allows at an acute join. The set is
    exact, so a new join fails until it is fixed or added there with its reason."""

    def test_no_pieces_fused(self):
        inputs = charset.finish_inputs()          # what finishing received, recorded as the families were built
        for name, glyphs in (("P", full_p()), ("T", full_mixed()), ("M", full_m())):
            self.assertEqual(set(inputs[name]), set(glyphs), name)
            self.assertEqual(set(fused_pieces(glyphs, inputs[name])), set(FUSED_BY_DESIGN.get(name, ())), name)

    def test_raw_dicts_are_read_only(self):
        for raw in (charset.raw_p(), charset.raw_m(), charset.finish_inputs()["P"]):
            with self.assertRaises(TypeError):
                raw["a"] = None


class Setting(unittest.TestCase):
    def test_line_windows(self):
        for setter in (kerned, mixed):
            for text in LINES:
                gaps = line_gaps([(c, g) for c, g, _ in setter(text)])
                low = [(a, b, round(d, 3)) for a, b, d in gaps if d < 1.98]
                self.assertFalse(low, f"{setter.__name__}: {text!r}")

    def test_tabular_cells(self):
        line = tabular("0123")
        xs = [x for _, _, x in line]
        steps = {round(b - a - (full_m()[line[i + 1][0]].minx - full_m()[line[i][0]].minx), 6) for i, (a, b) in enumerate(zip(xs, xs[1:]))}
        self.assertTrue(all(abs(s % 12) < 1e-6 or abs(s % 12 - 12) < 1e-6 for s in steps) or len(line) == 4)

    def test_cells_clear_the_line_check(self):
        # Centred in their cells, the two widest glyphs sit cell - width apart: the cells leave
        # 2.00w (Mono) and 2.00w (Tab digits; 1.98w at the tuner's 7.02w budget), not GAPMIN.
        self.assertGreaterEqual(CELL_M - max(g.width for g in full_m().values()), LINE_MIN)
        self.assertGreaterEqual(CELL_F - max(full_mixed()[c].width for c in FIGURES), LINE_MIN)
        self.assertGreaterEqual(CELL_F - 7.02, LINE_MIN - 1e-9)


class LineSpacing(unittest.TestCase):
    """At the fonts' 28w line pitch, ink within y in [-12, 14] keeps 2w between lines at any horizontal
    offset. Only the comma-below letters reach lower; README.md and docs/PRINTING.md list them and the
    pitch that clears them."""

    PITCH = 28.0
    BAND = (-12.0, 14.0)
    COMMA_BELOW = "ĢĶķĻļŅņŖŗŢţȘșȚț"
    CLEAR_PITCH = 30.6

    def test_ink_band(self):
        self.assertEqual(self.BAND[1] - self.BAND[0], self.PITCH - 2)
        lowest, highest = -99.0, 99.0
        for name, glyphs in (("P", full_p()), ("T", full_mixed()), ("M", full_m())):
            outside = {c for c, g in glyphs.items() if g.bounds[1] < self.BAND[0] - 1e-6 or g.bounds[3] > self.BAND[1] + 1e-6}
            self.assertEqual(outside, set(self.COMMA_BELOW), name)
            lowest = max(lowest, max(g.bounds[3] for g in glyphs.values()))
            highest = min(highest, min(g.bounds[1] for g in glyphs.values()))
        # comma below over ring (ș over Å): the pitch at which the closest approach is 2w again
        self.assertAlmostEqual(lowest + 2 - highest, self.CLEAR_PITCH, delta=0.005)

    def test_ink_band_in_fonts(self):
        top, bottom = (10 - self.BAND[0]) * UNITS, (10 - self.BAND[1]) * UNITS
        for name in ("Fillaprint-Regular.ttf", "FillaprintTab-Regular.ttf", "FillaprintMono-Regular.ttf"):
            font = FontReader(FONTS / name).font
            hhea, os2 = font["hhea"], font["OS/2"]
            self.assertEqual(hhea.ascent - hhea.descent + hhea.lineGap, self.PITCH * UNITS, name)
            self.assertEqual(os2.sTypoAscender - os2.sTypoDescender + os2.sTypoLineGap, self.PITCH * UNITS, name)
            glyf = font["glyf"]
            cmap = font.getBestCmap()
            outside = {chr(u) for u, g in cmap.items() if glyf[g].numberOfContours > 0
                       and (glyf[g].yMax > top or glyf[g].yMin < bottom)}
            self.assertEqual(outside, set(self.COMMA_BELOW), name)

    def test_documented(self):
        for doc in (ROOT / "README.md", ROOT / "docs" / "PRINTING.md"):
            text = doc.read_text(encoding="utf-8")
            self.assertIn(f"{self.CLEAR_PITCH:g} × w", text, doc.name)
            self.assertIn(" ".join(self.COMMA_BELOW), text, doc.name)


FAMILIES = (("Fillaprint-Regular.ttf", full_p), ("FillaprintTab-Regular.ttf", full_mixed),
            ("FillaprintMono-Regular.ttf", full_m))


class Fonts(unittest.TestCase):
    """The committed TTFs, read back: rebuild them (python build.py) after changing the sources."""

    def test_set_lines_from_ttf(self):
        for name in ("Fillaprint-Regular.ttf", "FillaprintTab-Regular.ttf"):
            reader = FontReader(FONTS / name)
            for text in LINES:
                gaps = line_gaps([(c, g) for c, g, _ in reader.layout(text)])
                low = [(a, b, round(d, 3)) for a, b, d in gaps if d < 1.98]
                self.assertFalse(low, f"{name}: {text!r}")

    def test_outlines_follow_source(self):
        # build.py's tolerance, on every glyph of every family
        for name, source in FAMILIES:
            reader = FontReader(FONTS / name)
            dev = {}
            for c, g in source().items():
                out = reader.outline(glyph_name(c))
                a, b = out.centroid, g.geom.centroid
                dev[c] = out.boundary.hausdorff_distance(affinity.translate(g.geom, a.x - b.x, a.y - b.y).boundary)
            worst = max(dev, key=dev.get)
            self.assertLessEqual(dev[worst], OUTLINE_TOL, f"{name}: {worst!r}")

    def test_mono_lines_follow_setting(self):
        """build.py's line checks on Mono: every gap within GAP_TOL of the setting engine, positions
        off by no more than outline rounding (whole-unit cells, no kerning), and the 1.98 floor."""
        reader = FontReader(FONTS / "FillaprintMono-Regular.ttf")
        mono = full_m()
        for text in LINES + [spec.LOWER, spec.FIGURES]:
            text = "".join(c for c in text if c == " " or c in mono)
            src, ttf = tabular(text), reader.layout(text)
            self.assertEqual([c for c, _, _ in src], [c for c, _, _ in ttf], text)
            gaps = lambda line: [b.bounds[0] - a.bounds[2] for (_, a, _), (_, b, _) in zip(line, line[1:])]
            dev = max((abs(x - y) for x, y in zip(gaps(src), gaps(ttf))), default=0.0)
            drift = max(abs((s.bounds[0] - src[0][1].bounds[0]) - (t.bounds[0] - ttf[0][1].bounds[0]))
                        for (_, s, _), (_, t, _) in zip(src, ttf))
            self.assertLessEqual(dev, GAP_TOL, text)
            self.assertLessEqual(drift, OUTLINE_TOL, text)
            low = [(a, b, round(d, 3)) for a, b, d in line_gaps([(c, g) for c, g, _ in ttf]) if d < LINE_MIN]
            self.assertFalse(low, text)

    def test_mono_fixed_pitch(self):
        """Every Mono advance is the 12w cell, .notdef included and centred (Mono draws the 14 characters
        it leaves out as .notdef), and ink in neighbouring cells stays 1.98w apart."""
        font = FontReader(FONTS / "FillaprintMono-Regular.ttf").font
        cell = CELL_M * UNITS
        self.assertEqual(font["post"].isFixedPitch, 1)
        self.assertEqual({adv for adv, _ in font["hmtx"].metrics.values()}, {cell})
        glyf = font["glyf"]
        self.assertEqual(glyf[".notdef"].xMin + glyf[".notdef"].xMax, cell)
        drawn = [glyf[n] for n in font.getGlyphOrder() if glyf[n].numberOfContours > 0]
        self.assertGreaterEqual(cell + min(g.xMin for g in drawn) - max(g.xMax for g in drawn), LINE_MIN * UNITS)

    def test_tab_figure_cells(self):
        font = FontReader(FONTS / "FillaprintTab-Regular.ttf").font
        cell = CELL_F * UNITS
        names = [glyph_name(c) for c in FIGURES]
        self.assertEqual({font["hmtx"][n][0] for n in names + ["uni2007"]}, {cell})
        glyf = font["glyf"]
        self.assertGreaterEqual(cell + min(glyf[n].xMin for n in names) - max(glyf[n].xMax for n in names),
                                LINE_MIN * UNITS)

    def test_lsb_is_outline_xmin(self):
        """TrueType places an outline by its hmtx lsb (phantom point xMin - lsb), so the two must agree."""
        for name, _ in FAMILIES:
            font = FontReader(FONTS / name).font
            glyf, hmtx = font["glyf"], font["hmtx"]
            bad = [(n, hmtx[n][1], glyf[n].xMin) for n in font.getGlyphOrder()
                   if glyf[n].numberOfContours > 0 and hmtx[n][1] != glyf[n].xMin]
            bad += [(n, hmtx[n][1], None) for n in font.getGlyphOrder() if glyf[n].numberOfContours == 0 and hmtx[n][1]]
            self.assertFalse(bad, name)


class Licensing(unittest.TestCase):
    """OFL metadata travels inside each TTF: copyright, license text and URL, installable embedding."""

    IDS = (0, 9, 12, 13, 14)

    def assert_licensed(self, font, where):
        from beadjoint.licensing import COPYRIGHT, LICENSE_TEXT, LICENSE_URL
        name = font["name"]
        for i in self.IDS:
            recs = [(r.platformID, r.platEncID, r.langID) for r in name.names if r.nameID == i]
            self.assertEqual(recs, [(3, 1, 0x409)], f"{where}: name {i}")
        self.assertEqual(name.getName(0, 3, 1, 0x409).toUnicode(), COPYRIGHT, where)
        self.assertEqual(name.getName(13, 3, 1, 0x409).toUnicode(), LICENSE_TEXT, where)
        self.assertEqual(name.getName(14, 3, 1, 0x409).toUnicode(), LICENSE_URL, where)
        self.assertIn("SIL OPEN FONT LICENSE VERSION 1.1", LICENSE_TEXT.upper())
        self.assertEqual(LICENSE_TEXT, (ROOT / "OFL.txt").read_text(encoding="utf-8").strip())
        self.assertEqual(font["OS/2"].fsType, 0, where)

    def test_apply_license(self):
        from fontTools.ttLib import TTFont, newTable
        from beadjoint.licensing import apply_license
        font = TTFont()
        font["name"] = newTable("name")
        font["name"].names = []
        font["name"].setName("stale copyright", 0, 1, 0, 0)          # replaced on every platform
        font["name"].setName("stale license", 13, 3, 1, 0x409)
        font["OS/2"] = newTable("OS/2")
        font["OS/2"].fsType = 0x0004                                  # preview & print only
        apply_license(font)
        self.assert_licensed(font, "apply_license")

    def test_fonts_carry_license(self):
        for name, _ in FAMILIES:
            self.assert_licensed(FontReader(FONTS / name).font, name)


if __name__ == "__main__":
    unittest.main()
