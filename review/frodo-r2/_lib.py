"""Frodo r2 (accents) prototyping helpers. Review only; nothing here is imported by the build."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shapely import affinity
from shapely.ops import unary_union
from beadjoint.geom import S, So, D, Rect, finish, BALL as B, rotate180
from beadjoint.latin import diagonal, mirror_x, shift
from beadjoint import marks
from beadjoint.marks import SHAPES, compose, decompose, place_above, place_below
from beadjoint.verify import check_glyph
from beadjoint.glyphs import Glyph, pieces
from beadjoint.sheet import grid
from beadjoint.charset import full_p, full_mixed, raw_p, CHARS
from beadjoint.setting import mixed
from beadjoint.verify import line_gaps
from beadjoint.specimen import draw_rows

R = str(Path(__file__).resolve().parents[2] / "review/frodo-r2")


def min_piece_gap(f):
    ps = pieces(f)
    if len(ps) < 2:
        return None
    return min(a.distance(b) for i, a in enumerate(ps) for b in ps[i + 1:])


def audit(name, f):
    r = check_glyph(f)
    gap = min_piece_gap(f)
    b = [round(v, 2) for v in f.bounds]
    flag = "" if (not r["thin"] and not r["islands"] and (gap is None or gap >= 1.98)) else "  <-- FAIL"
    print(f"{name:10s} T {r['thickness']:.2f} thin {r['thin']} isl {r['islands']} gap {gap if gap is None else round(gap, 2)} "
          f"pieces {len(pieces(f))} bounds {b}{flag}")
    return r


def glyphs_with(overrides):
    g = dict(full_mixed())
    for c, geom in overrides.items():
        g[c] = Glyph(c, f"F:{c}:{id(geom)}", geom)
    return g


def text(overrides, rows, path, scale=7):
    g = glyphs_with(overrides)
    out = [(cap, [mixed(l, g) for l in lines]) for cap, lines in rows]
    draw_rows(out, scale=scale, path=fr"{R}\{path}")
    return g


def sheet(d, path, cols=10, scale=8, cell=(20, 30)):
    out = {}
    for k, geom in d.items():
        out[k] = Glyph(k[0], k, geom)
    grid(out, fr"{R}\{path}", cols=cols, scale=scale, cell=cell)
