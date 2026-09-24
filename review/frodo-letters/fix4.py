from _lib import *
exec(open(r"F:\code\beadjoint\review\frodo-letters\mw.py", encoding="utf-8").read().split("cand = {}")[0])
exec(open(r"F:\code\beadjoint\review\frodo-letters\n.py", encoding="utf-8").read().split("cand = {")[0])
NEW = {
    "N": N_edge(9),
    "M": M_v(5, r=2),
    "W": rotate180(M_v(5, r=2), (5, 3)),
    "S": S((6, -3, B), (1, -3, 2), (1, 2, 2), (6, 4, 2), (6, 9, 2), (1, 9, B)),
    "G": S((6, -1, B), (6, -3), (1, -3, 2), (1, 9, 2), (6, 9), (6, 3), (4, 3)),
    "C": S((6, -3, B), (1, -3, 2), (1, 9, 2), (6, 9, B)),
    "R": S((1, -4), (1, 10)) | S((1, -3), (6, -3), (6, 3), (1, 3)) | S((3.5, 3), (6.5, 9, B)),
    "K": S((1, -4), (1, 10)) | S((6.5, -3, B), (2.5, 3), (6.5, 9, B)),
    "ß": S((1, 10), (1, -3, 2), (5.5, -3), (5.5, 2)) | S((4, 2), (6.5, 2), (6.5, 9), (5, 9, B)),
}
FIN = {c: finish(g) for c, g in NEW.items()}
if __name__ == "__main__":
    words = ["A R AR RA 12-A 12-R ARRAY", "B8 8B DO 0D O0 D0 I1l| Z2 2Z", "KRAKEN BIN 12-R ROOM",
             "Straße größeren Fuß STRASSE", "k K kK Kk rn m cl d uv"]
    rows = []
    for cap, ov in [("now", {}), ("fixes", FIN)]:
        g = dict(full_mixed())
        for c, geom in ov.items():
            g[c] = Glyph(c, f"F:{c}:{id(geom)}", geom)
        rows.append((cap, [mixed(w, g) for w in words]))
    draw_rows(rows, scale=4, path=fr"{R}\fix4_text.png")
    sheet(NEW, "fix4.png", refs="AB8k", cols=13, scale=8, cell=(14, 24))
