"""Frodo's prototyping helpers (review only; nothing here is imported by the build)."""
import math
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shapely import affinity
from shapely.ops import unary_union
from beadjoint.geom import S, So, D, Rect, finish, BALL as B, rotate180, solve
from beadjoint.latin import diagonal, mirror_x, shift
from beadjoint.verify import check_glyph
from beadjoint.glyphs import Glyph, pieces
from beadjoint.sheet import grid
from beadjoint.charset import full_p, full_mixed
from beadjoint.setting import mixed
from beadjoint.specimen import draw_rows

R = str(Path(__file__).resolve().parents[2] / "review/frodo-letters")
P = full_p()


def edge_diag(xa, ya, xb, yb, side_a=-1, side_b=+1, clip=(-4.0, 10.0)):
    """2w diagonal whose EDGES (not centreline) pass through (xa, ya) and (xb, yb): the edge on
    side_a (-1 = left of travel... solved numerically) meets a, the opposite edge meets b."""
    # centreline through a + n*side_a and b + n*side_b, n the unit normal; iterate (n depends on the line)
    ca, cb = (xa, ya), (xb, yb)
    for _ in range(30):
        dx, dy = cb[0] - ca[0], cb[1] - ca[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        ca = (xa - side_a * nx, ya - side_a * ny)
        cb = (xb - side_b * nx, yb - side_b * ny)
    return diagonal(ca[0], ca[1], cb[0], cb[1], clip=clip)


def report(name, raw):
    f = finish(raw)
    r = check_glyph(f)
    b = [round(v, 2) for v in f.bounds]
    npieces = len(pieces(f))
    print(f"{name:28s} T {r['thickness']:.2f} at {tuple(float(v) for v in r['at'])} thin {r['thin']} islands {r['islands']} bounds {b} pieces {npieces}")
    return f


def min_piece_gap(f):
    ps = pieces(f)
    if len(ps) < 2:
        return None
    return min(a.distance(b) for i, a in enumerate(ps) for b in ps[i + 1:])


def sheet(cands, path, refs="", cols=8, scale=8, cell=(24, 26)):
    out = {}
    for k, raw in cands.items():
        f = report(k, raw)
        out[k] = Glyph(k[0], k, f)
    for c in refs:
        out[c] = P[c]
    grid(out, fr"{R}\{path}", cols=cols, scale=scale, cell=cell)
    return out


def text(overrides, rows, path, scale=7):
    """Set lines with some glyphs replaced; overrides: {char: finished geom}."""
    g = dict(full_mixed())
    for c, geom in overrides.items():
        g[c] = Glyph(c, f"F:{c}:{id(geom)}", geom)
    out = []
    for cap, lines in rows:
        out.append((cap, [mixed(l, g) for l in lines]))
    draw_rows(out, scale=scale, path=fr"{R}\{path}")
