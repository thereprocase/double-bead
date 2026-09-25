import sys
from pathlib import Path; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shapely.ops import unary_union

from beadjoint.geom import BALL as B, D, Rect, S, So, finish
from beadjoint.latin import mirror_x, shift, small_figures
from beadjoint.glyphs import _raw_p, Glyph
from beadjoint.verify import check_glyph
from beadjoint.sheet import grid
from shapely.strtree import STRtree

fig = _raw_p()  # raw figures 0-9 for small_figures()

s = {}

# existing family reference pieces (raw, unfinished) needed for reuse
s["<"] = S((6, -1, B), (1, 3), (6, 7, B))
s[">"] = mirror_x(s["<"], 7)
s["="] = S((0.5, 0.5), (6.5, 0.5)) | S((0.5, 5.5), (6.5, 5.5))
s["~"] = S((0.5, 4, B), (2.5, 2), (4.5, 4), (6.5, 2, B))
s["±"] = S((0, 1), (6, 1)) | S((3, -2), (3, 4)) | S((0, 8), (6, 8))

# --- Omega ------------------------------------------------------------------
s["Ω"] = S((-0.5, 9, B), (1.5, 7, 1.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 7, 1.5), (8.5, 9, B))
s["\u2126"] = s["Ω"]   # Ohm sign maps to the same glyph

# --- eighths (extend the ¼ ½ ¾ construction) --------------------------------
small = small_figures(fig)
raised = {k: shift(v, 0, -4) for k, v in small.items()}
frac_slash = diagonal = None
import math
def diagonal2(x0, y0, x1, y1, clip=(-4.0, 10.0)):
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    line = S((x0 - ux * 2, y0 - uy * 2), (x1 + ux * 2, y1 + uy * 2))
    return line.intersection(Rect(-20, clip[0], 40, clip[1]))
frac_slash = diagonal2(0.9, 10, 4.9, -4)
fracs = {"¼": ("1", "4"), "½": ("1", "2"), "¾": ("3", "4"),
         "⅛": ("1", "8"), "⅜": ("3", "8"), "⅝": ("5", "8"), "⅞": ("7", "8")}
for ch, (n, d) in fracs.items():
    num = raised[n]
    sl = shift(frac_slash, num.bounds[2] + 1.2)
    den = shift(small[d], sl.bounds[2] + 1.2 - small[d].bounds[0])
    s[ch] = unary_union([num, sl, den])

# --- arrows -------------------------------------------------------------
s["→"] = S((0, 3, B), (7, 3)) | S((3, -1, B), (7, 3), (3, 7, B))
s["←"] = mirror_x(s["→"], s["→"].bounds[2] + s["→"].bounds[0])
s["↓"] = S((3, 0, B), (3, 7)) | S((-1, 3, B), (3, 7), (7, 3, B))
s["↑"] = S((3, 7, B), (3, 0)) | S((-1, 3, B), (3, 0), (7, 3, B))

# --- comparisons -------------------------------------------------------
s["≤"] = S((5, -2, B), (1, 1), (5, 4, B)) | S((1, 8), (5, 8))
s["≥"] = mirror_x(s["≤"], s["≤"].bounds[2] + s["≤"].bounds[0])
s["≈"] = shift(s["~"], 0, -3) | shift(s["~"], 0, 3)

new_glyphs = ["Ω", "\u2126", "⅛", "⅜", "⅝", "⅞", "→", "←", "↑", "↓", "≤", "≥", "≈"]

print("=== check_glyph on raw (pre-finish) ===")
for c in new_glyphs:
    r = check_glyph(s[c])
    print(f"{c!r:>4} thick={r['thickness']:.2f} thin={r['thin']} islands={r['islands']} tight={r['tight']} bounds={[round(b,2) for b in s[c].bounds]}")

print()
print("=== check_glyph on finished ===")
finished = {c: finish(s[c]) for c in new_glyphs}
for c in new_glyphs:
    r = check_glyph(finished[c])
    ok = "OK" if r["ok"] else "FAIL"
    print(f"{c!r:>4} [{ok}] thick={r['thickness']:.2f} thin={r['thin']} islands={r['islands']}")

print()
print("=== piece distances (>= 2 required) ===")
from beadjoint.glyphs import pieces
for c in new_glyphs:
    pcs = pieces(finished[c])
    if len(pcs) < 2:
        continue
    dmin = min(pcs[i].distance(pcs[j]) for i in range(len(pcs)) for j in range(i + 1, len(pcs)))
    print(f"{c!r:>4} pieces={len(pcs)} min_dist={dmin:.3f}")

glyphs_for_grid = {f"n{i}_{c}": Glyph(c, f"X:{c}", finished[c]) for i, c in enumerate(new_glyphs)}
grid(glyphs_for_grid, str(Path(__file__).resolve().parents[2] / "review/frodo-r5/new_glyphs.png"), cols=7, scale=16)
print("wrote new_glyphs.png")
