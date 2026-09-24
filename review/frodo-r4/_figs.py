"""Frodo r4: figure widths, figure-figure gaps in P (optical) vs Tab (9w cells), and letter reference gaps."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
import numpy as np
from beadjoint.charset import full_p, full_mixed
from beadjoint.setting import off, cell_origin, CELL_F, _distance, _profile, BAND_FIG, BAND_X, T, DEPTH

P = full_p()
M = full_mixed()
F = "0123456789"
print("figure ink widths:", {c: round(M[c].width, 2) for c in F})


def bbox_gap(a, b, dx):
    return b.minx + dx - a.maxx


def mean_gap(a, b, dx, band):
    _, ra = _profile(a, band)
    lb, _ = _profile(b, band)
    both = ~np.isnan(ra) & ~np.isnan(lb)
    g = dx + lb[both] - ra[both]
    return float(g.mean()) if both.any() else float("nan"), float(g.min()) if both.any() else float("nan")


print("\nfigure pairs: P optical (true gap / mean shared-scanline gap)   vs   Tab cells (true / mean)")
tab_true, p_true = [], []
for a in F:
    row = []
    for b in F:
        ga, gb = P[a], P[b]
        dp = off(ga, gb)
        ta, tb = M[a], M[b]
        dt = cell_origin(1, tb, CELL_F) - cell_origin(0, ta, CELL_F)
        tp, tt = _distance(ga, gb, dp), _distance(ta, tb, dt)
        mp, mt = mean_gap(ga, gb, dp, BAND_FIG)[0], mean_gap(ta, tb, dt, BAND_FIG)[0]
        p_true.append(tp)
        tab_true.append(tt)
        row.append(f"{a}{b} {tp:.2f}/{mp:.2f} | {tt:.2f}/{mt:.2f}")
    print("  " + "   ".join(row[:5]))
    print("  " + "   ".join(row[5:]))
print(f"\nP  true gap: min {min(p_true):.2f} mean {np.mean(p_true):.2f} max {max(p_true):.2f}")
print(f"Tab true gap: min {min(tab_true):.2f} mean {np.mean(tab_true):.2f} max {max(tab_true):.2f}")

print("\nreference letter pairs (mean shared-scanline gap / true gap):")
for pair in ["nn", "HH", "HO", "OO", "nu", "oo", "ll", "Ha", "Hn", "Ex", "Mx", "ME", "EE", "NU", "0.", "3.", ".2", "-2",
             "2-", "8-", "-3", "1-", "-1", "0k", "k-", "4V", "V~", "#8", "#3", "Ø1", "Mx", "m²", "3.", "µF", "(t", ".)",
             "e-", "-m", "a_", "_b", ":3", "2:", ":5", "M3", "M4", "M6", "G1", "12", "1/", "/4", "4\"", "8\"", "2\"",
             "\"-", "t.", ".\"", "x2", "×2", "24", "4V", "V ", "5A", "T2", "25", "R2", "2.", ".5", "No", "o."]:
    if " " in pair:
        continue
    a, b = M[pair[0]], M[pair[1]]
    band = BAND_FIG if (a.tall or b.tall) else BAND_X
    dx = off(a, b)
    mg, mn = mean_gap(a, b, dx, band)
    print(f"  {pair}: mean {mg:.2f}  min-row {mn:.2f}  true {_distance(a, b, dx):.2f}  bbox {bbox_gap(a, b, dx):.2f}  band {band}")
