"""Frodo's proposed capitals/specials, in latin.py notation, checked against the prototypes."""
from _lib import *
exec(open(str(Path(__file__).resolve().parents[2] / "review/frodo-letters/fix4.py"), encoding="utf-8").read().split('if __name__')[0])
from beadjoint.glyphs import _raw_p
from beadjoint.latin import capitals
from beadjoint.marks import apostrophe

# --- solve the constants once (printed so they can be pasted as literals) ---
cN = 1.0
for _ in range(60):
    cN = math.hypot(9 - 2 * cN, 14) / 14
cM = 1.0
for _ in range(60):
    cM = math.hypot(5 - cM, 9) / 9
L = math.hypot(5 - cM, 9); ux, uy = (5 - cM) / L, 9 / L
print(f"N: c = {cN:.4f}  ->  diagonal({cN:.3f}, -4, {9 - cN:.3f}, 10)")
print(f"M: c = {cM:.4f}  arm start = ({cM - 2 * ux:.3f}, {-4 - 2 * uy:.3f})  end = ({10 - cM + 2 * ux:.3f}, {-4 - 2 * uy:.3f})")

p, cap = _raw_p(), capitals()
lit = {
    "N": S((1, 10), (1, -4)) | S((8, -4), (8, 10)) | diagonal(1.111, -4, 7.889, 10),
    "M": S((1, 10), (1, -4)) | S((9, -4), (9, 10))
         | S((0.293, -5.834), (5, 5, 2), (9.707, -5.834)).intersection(Rect(-20, -4, 40, 10)),
}
lit["W"] = rotate180(lit["M"], (5, 3))
for k in ("N", "M", "W"):
    d = finish(lit[k]).symmetric_difference(FIN[k]).area
    print(k, "literal vs prototype sym-diff area", round(d, 4))
lit.update({k: NEW[k] for k in "SGCRKß"})
lit["ŀ"] = p["l"] | D((5, 5))
lit["ľ"] = p["l"] | apostrophe(5.6)
lit["Ľ"] = cap["L"] | apostrophe(5.6)
out = {}
for k, g in lit.items():
    f = finish(g); r = check_glyph(f); gap = min_piece_gap(f)
    ok = not r["thin"] and not r["islands"] and (gap is None or gap >= 1.98)
    print(f"{k}  T {r['thickness']:.2f}  thin {r['thin']}  islands {r['islands']}  piece gap {gap if gap is None else round(gap, 2)}  "
          f"width {f.bounds[2] - f.bounds[0]:.2f}  {'OK' if ok else 'FAIL'}")
    out[k] = Glyph(k, "D:" + k, f)
for c in "56AB8H":
    out[c] = P[c]
grid(out, fr"{R}\decisions.png", cols=9, scale=9, cell=(14, 24))
