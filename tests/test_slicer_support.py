"""Slicer support tests: gcode move parsing and 3MF mesh helpers (standard library only).

    python -m unittest discover -s tests      (from the repo root)
"""
import math
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo"))

import slicer_support as ss  # noqa: E402


class MovePieces(unittest.TestCase):
    def test_line_extrudes(self):
        segs, x, y, e = ss.move_pieces("G1 X10 Y5 E0.4 ; wall", 0.0, 0.0)
        self.assertEqual(segs, [(0.0, 0.0, 10.0, 5.0)])
        self.assertEqual((x, y, e), (10.0, 5.0, 0.4))

    def test_travel_keeps_missing_axis(self):
        segs, x, y, e = ss.move_pieces("G0 X3", 1.0, 2.0)
        self.assertEqual((x, y, e), (3.0, 2.0, 0.0))
        self.assertEqual(segs, [(1.0, 2.0, 3.0, 2.0)])

    def test_non_move_is_ignored(self):
        self.assertEqual(ss.move_pieces("G92 E0", 1.0, 2.0), ([], 1.0, 2.0, 0.0))

    def test_ccw_quarter_arc(self):
        # G3 from (1,0) to (0,1) about the origin: a quarter circle of radius 1.
        segs, x, y, e = ss.move_pieces("G3 X0 Y1 I-1 J0 E0.2", 1.0, 0.0)
        self.assertEqual((x, y), (0.0, 1.0))
        length = sum(math.hypot(bx - ax, by - ay) for ax, ay, bx, by in segs)
        self.assertAlmostEqual(length, math.pi / 2, delta=1e-3 * math.pi / 2)  # chords run slightly short of the arc
        self.assertTrue(all(math.hypot(bx - ax, by - ay) <= ss.ARC_SEG + 1e-9 for ax, ay, bx, by in segs))
        for ax, ay, _, _ in segs:
            self.assertAlmostEqual(math.hypot(ax, ay), 1.0, places=6)
            self.assertGreaterEqual(ax, -1e-9)
            self.assertGreaterEqual(ay, -1e-9)

    def test_cw_arc_goes_the_other_way(self):
        # G2 from (1,0) to (0,1) about the origin sweeps three quarters, through negative y.
        segs, _, _, _ = ss.move_pieces("G2 X0 Y1 I-1 J0", 1.0, 0.0)
        length = sum(math.hypot(bx - ax, by - ay) for ax, ay, bx, by in segs)
        self.assertAlmostEqual(length, 3 * math.pi / 2, delta=1e-3 * 3 * math.pi / 2)  # chords run slightly short of the arc
        self.assertTrue(any(ay < -0.5 for _, ay, _, _ in segs))

    def test_full_circle(self):
        segs, _, _, _ = ss.move_pieces("G2 X1 Y0 I-1 J0", 1.0, 0.0)
        length = sum(math.hypot(bx - ax, by - ay) for ax, ay, bx, by in segs)
        self.assertAlmostEqual(length, 2 * math.pi, delta=1e-3 * 2 * math.pi)  # chords run slightly short of the arc


def _cube_triangles():
    v = [(x, y, z) for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)]
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [[v[a], v[b], v[c]] for a, b, c, d in quads for a, b, c in ((a, b, c), (a, c, d))]


class Mesh(unittest.TestCase):
    def _write(self, path, binary):
        tris = _cube_triangles()
        if binary:
            data = bytearray(80) + struct.pack("<I", len(tris))
            for t in tris:
                data += struct.pack("<12fH", 0, 0, 0, *t[0], *t[1], *t[2], 0)
            path.write_bytes(bytes(data))
        else:
            lines = ["solid cube"]
            for t in tris:
                lines += ["facet normal 0 0 0", "outer loop"] + [f"vertex {x} {y} {z}" for x, y, z in t]
                lines += ["endloop", "endfacet"]
            path.write_text("\n".join(lines + ["endsolid cube"]))

    def test_binary_and_ascii_index_the_same_cube(self):
        with tempfile.TemporaryDirectory() as d:
            for binary in (True, False):
                p = Path(d) / f"cube{binary}.stl"
                self._write(p, binary)
                verts, faces, lo, hi = ss.mesh(p)
                self.assertEqual(len(verts), 8)
                self.assertEqual(len(faces), 12)
                self.assertEqual((lo, hi), ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)))

    def test_add_mesh_writes_3mf_object(self):
        res = ET.Element(f"{{{ss.NS}}}resources")
        ss.add_mesh(res, 7, "cube", [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)])
        obj = res.find(f"{{{ss.NS}}}object")
        self.assertEqual((obj.get("id"), obj.get("name")), ("7", "cube"))
        self.assertEqual(len(obj.findall(f".//{{{ss.NS}}}vertex")), 3)
        self.assertEqual(obj.find(f".//{{{ss.NS}}}triangle").attrib, {"v1": "0", "v2": "1", "v3": "2"})


class Profiles(unittest.TestCase):
    def test_bundled_profiles_are_complete(self):
        self.assertEqual(ss.require_profiles(ROOT / "demo" / "profiles"), ROOT / "demo" / "profiles")

    def test_missing_profiles_explain_the_fix(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(SystemExit) as cm:
            ss.require_profiles(d)
        self.assertIn("demo/profiles/README.md", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
