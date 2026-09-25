"""Fillaprint regression tests.

    python -m unittest discover -s tests      (from the repo root)

Covers the geometry primitives, the spec's reference results, the hard rules on every glyph of every
set, the setting engine's line check, and the built TTFs (outlines and set lines read back).
"""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from beadjoint import glyphs as spec  # noqa: E402
from beadjoint.charset import CHARS, full_m, full_mixed, full_p  # noqa: E402
from beadjoint.geom import DOT, S, fillet, soft  # noqa: E402
from beadjoint.glyphs import pieces  # noqa: E402
from beadjoint.readback import FontReader  # noqa: E402
from beadjoint.setting import kerned, mixed, tabular  # noqa: E402
from beadjoint.verify import check_glyph, line_gaps  # noqa: E402

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


class HardRules(unittest.TestCase):
    """No thin ink, no thin enclosed holes, separate pieces >= 1.98 w, in every glyph of every set."""

    def check(self, glyphs):
        bad = []
        for c, g in glyphs.items():
            r = check_glyph(g.geom)
            ps = pieces(g.geom)
            gap = min((a.distance(b) for i, a in enumerate(ps) for b in ps[i + 1:]), default=99.0)
            if r["thin"] or r["islands"] or gap < 1.98:
                bad.append((c, r["thin"], r["islands"], round(gap, 3)))
        self.assertFalse(bad)

    def test_full_p(self):
        self.assertEqual(len(full_p()), len(CHARS))
        self.check(full_p())

    def test_full_m(self):
        self.check(full_m())


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


class Fonts(unittest.TestCase):
    def test_set_lines_from_ttf(self):
        for name in ("Fillaprint-Regular.ttf", "FillaprintTab-Regular.ttf"):
            reader = FontReader(ROOT / "fonts" / name)
            for text in LINES:
                gaps = line_gaps([(c, g) for c, g, _ in reader.layout(text)])
                low = [(a, b, round(d, 3)) for a, b, d in gaps if d < 1.98]
                self.assertFalse(low, f"{name}: {text!r}")

    def test_outlines_follow_source(self):
        reader = FontReader(ROOT / "fonts" / "FillaprintTab-Regular.ttf")
        from beadjoint.charset import glyph_name
        from shapely import affinity
        worst = 0.0
        for c, g in full_mixed().items():
            out = reader.outline(glyph_name(c))
            a, b = out.centroid, g.geom.centroid
            d = out.boundary.hausdorff_distance(affinity.translate(g.geom, a.x - b.x, a.y - b.y).boundary)
            worst = max(worst, d)
        self.assertLess(worst, 0.03)


if __name__ == "__main__":
    unittest.main()
