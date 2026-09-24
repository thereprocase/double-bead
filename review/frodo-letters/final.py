from _lib import *
from beadjoint import marks
exec(open(r"F:\code\beadjoint\review\frodo-letters\fix4.py", encoding="utf-8").read().split('if __name__')[0])
from beadjoint.glyphs import _raw_p
from beadjoint.latin import capitals
from beadjoint.marks import apostrophe
p, cap = _raw_p(), capitals()
FIN["ŀ"] = finish(p["l"] | D((5, 5)))
FIN["ľ"] = finish(p["l"] | apostrophe(5.6))
FIN["Ľ"] = finish(cap["L"] | apostrophe(5.6))
bases = {c: g.geom for c, g in P.items()}
bases.update(FIN)
comp = "ÑŃŇŅŴŚŜŞŠȘĜĞĠĢĆĈĊČŔŖŘĶ"
for ch in comp:
    b, ms = marks.decompose(ch)
    f = finish(marks.compose(ch, b, ms, bases))
    r = check_glyph(f)
    gap = min_piece_gap(f)
    assert not r["thin"] and not r["islands"], (ch, r)
    FIN[ch] = f
    print(ch, "T", r["thickness"], "gap", None if gap is None else round(gap, 2))
grid({c: Glyph(c, c, FIN[c]) for c in comp}, fr"{R}\final_composites.png", cols=11, scale=7, cell=(14, 30))
texts = [
    ("English caps", ["THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"]),
    ("Mixed", ["The quick brown fox jumps over the lazy dog.", "Falsches Üben von Xylophonmusik quält", "jeden größeren Zwerg. STRASSE Straße"]),
    ("Labels", ["1/4\" Jt.  1/2\" - 5/8\" dep.  M6 x 1.0  45°", "±0.1 mm  Ø12  24V DC  #3 PH  BIN 12-A  G1/4 S5 R2",
                "MIN MAX NEW WINDOW KRAKEN SAW GAUGE"]),
    ("Accents", ["ÑANDÚ Ńwin Ňoš Ŵales ŚĜŞŠȘ ĆČ ŘĶ ľud Ľubo col·lecció"]),
]
for scale, name in ((6, "final_text.png"), (2.5, "final_text_small.png")):
    rows = []
    for cap_, lines in texts:
        g = dict(full_mixed())
        for c, geom in FIN.items():
            g[c] = Glyph(c, f"F:{c}", geom)
        rows.append((cap_, [mixed(l, g) for l in lines]))
    draw_rows(rows, scale=scale, path=fr"{R}\{name}")
