from _lib import *
cand = {
    "G now": P["G"].geom,
    "G hook": S((6, -1, B), (6, -3), (1, -3), (1, 9), (6, 9), (6, 3), (4, 3)),
    "G hook r2": S((6, -1, B), (6, -3, 2), (1, -3, 2), (1, 9, 2), (6, 9, 2), (6, 3), (4, 3)),
    "G r2": S((6, -3, B), (1, -3, 2), (1, 9, 2), (6, 9, 2), (6, 3), (4, 3)),
    "6": P["6"].geom,
    "C": P["C"].geom,
    "O": P["O"].geom,
    "S r2": S((6, -3, B), (1, -3, 2), (1, 3, 2), (6, 3, 2), (6, 9, 2), (1, 9, B)),
    "S diag r2": S((6, -3, B), (1, -3, 2), (1, 0), (6, 6), (6, 9, 2), (1, 9, B)),
}
sheet(cand, "fix2.png", cols=9, scale=10, cell=(14, 24))
Sr2 = finish(cand["S r2"]); Sd = finish(cand["S diag r2"])
Gh = finish(cand["G hook"]); Ghr = finish(cand["G hook r2"]); Gr2 = finish(cand["G r2"])
rows = []
words = ["S5 5S SS55 G6 6G GG66 BIN S-56 G-36", "SLOT 5 GAUGE 6 SIZE 65 Sesam 5s"]
for cap, ov in [("now", {}), ("S r2, G hook", {"S": Sr2, "G": Gh}), ("S diag r2, G hook r2", {"S": Sd, "G": Ghr}),
                ("S r2, G r2", {"S": Sr2, "G": Gr2})]:
    g = dict(full_mixed())
    for c, geom in ov.items():
        g[c] = Glyph(c, f"F:{c}:{id(geom)}", geom)
    rows.append((cap, [mixed(w, g) for w in words]))
draw_rows(rows, scale=4, path=fr"{R}\fix2_text.png")
