from _lib import *
exec(open(r"F:\code\beadjoint\review\frodo-letters\mw.py", encoding="utf-8").read().split("cand = {}")[0])
exec(open(r"F:\code\beadjoint\review\frodo-letters\n.py", encoding="utf-8").read().split("cand = {")[0])
N9 = finish(N_edge(9))
M5, M4 = finish(M_v(5, r=2)), finish(M_v(4, r=2))
W1, W2 = finish(rotate180(M_v(5, r=2), (5, 3))), finish(rotate180(M_v(4, r=2), (5, 3)))
words = "MINIMUM WAVE VIEW NOW M6 M10 NUMBER HMNW Mom New Wien"
rows = [
    ("A: N9 + squared M/W", {"N": N9}),
    ("B: N9 + M v5 rv2 + W ^1 rv2", {"N": N9, "M": M5, "W": W1}),
    ("C: N9 + M v4 rv2 + W ^2 rv2", {"N": N9, "M": M4, "W": W2}),
    ("D: N9 + M v5 rv2 + squared W", {"N": N9, "M": M5}),
]
for scale, name in ((6, "mw_text2.png"), (2.5, "mw_text2_small.png")):
    out = []
    for cap, ov in rows:
        g = dict(full_mixed())
        for c, geom in ov.items():
            g[c] = Glyph(c, f"F:{c}:{id(geom)}", geom)
        out.append((cap, [mixed(words, g)]))
    draw_rows(out, scale=scale, path=fr"{R}\{name}")
grid({"M5": Glyph("M", "a", M5), "W1": Glyph("W", "b", W1), "M4": Glyph("M", "c", M4), "W2": Glyph("W", "d", W2),
      "N9": Glyph("N", "e", N9), "V": P["V"], "H": P["H"], "A": P["A"]}, fr"{R}\mw_pick.png", cols=8, scale=11, cell=(14, 24))
