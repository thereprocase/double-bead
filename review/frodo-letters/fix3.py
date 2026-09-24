from _lib import *
cand = {
    "S r2": S((6, -3, B), (1, -3, 2), (1, 3, 2), (6, 3, 2), (6, 9, 2), (1, 9, B)),
    "S slant r2": S((6, -3, B), (1, -3, 2), (1, 2, 2), (6, 4, 2), (6, 9, 2), (1, 9, B)),
    "S diag r2": S((6, -3, B), (1, -3, 2), (1, 0), (6, 6), (6, 9, 2), (1, 9, B)),
    "G hook": S((6, -1, B), (6, -3), (1, -3), (1, 9), (6, 9), (6, 3), (4, 3)),
    "G hook L2": S((6, -1, B), (6, -3), (1, -3, 2), (1, 9, 2), (6, 9), (6, 3), (4, 3)),
    "G r2": S((6, -3, B), (1, -3, 2), (1, 9, 2), (6, 9, 2), (6, 3), (4, 3)),
    "C r2": S((6, -3, B), (1, -3, 2), (1, 9, 2), (6, 9, B)),
}
fs = sheet(cand, "fix3.png", refs="56CO", cols=11, scale=10, cell=(14, 24))
words = ["S5 5S SS55 G6 6G GG66 C6 CG", "SLOT 5 GAUGE 6 SIZE 65 SCREW", "Sesam Gas 5s 6g Size Glass"]
rows = []
for cap, ov in [("now", {}), ("S r2, G r2, C r2", {"S": "S r2", "G": "G r2", "C": "C r2"}),
                ("S slant r2, G hook L2", {"S": "S slant r2", "G": "G hook L2"}),
                ("S diag r2, G hook", {"S": "S diag r2", "G": "G hook"})]:
    g = dict(full_mixed())
    for c, k in ov.items():
        g[c] = Glyph(c, f"F:{c}:{k}", fs[k].geom)
    rows.append((cap, [mixed(w, g) for w in words]))
draw_rows(rows, scale=4, path=fr"{R}\fix3_text.png")
