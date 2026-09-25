import sys
from pathlib import Path, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p, CHARS
from beadjoint.verify import check_glyph
import acute
P = full_p()
A = acute.full_acute()
rows, bad = [], []
for c in CHARS:
    a = check_glyph(P[c].geom); b = check_glyph(A[c].geom)
    if b["thin"] or b["islands"]:
        bad.append((c, b["thin"], b["islands"]))
    rows.append((c, a["thickness"], b["thickness"], round(P[c].geom.area - A[c].geom.area, 3)))
json.dump(rows, open(str(Path(__file__).resolve().parents[2] / "review/frodo-r3/cmp_acute.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("thin/islands in acute set:", bad)
ch = [r for r in rows if abs(r[1] - r[2]) > 0.02]
print(len(ch), "glyphs change max thickness; area removed max", max(r[3] for r in rows))
print("max thickness cur", max(r[1] for r in rows), "acute", max(r[2] for r in rows))
from collections import Counter
print("cur >2.9:", sum(1 for r in rows if r[1] > 2.9), " acute >2.9:", sum(1 for r in rows if r[2] > 2.9))
print(" ".join(f"{c}:{x:.2f}->{y:.2f}" for c, x, y, _ in ch[:400]))
