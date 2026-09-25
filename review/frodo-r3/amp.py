"""Frodo r3: & variants (raw strokes -> finished), drawn big with the fill_pinches additions shaded."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw
from beadjoint.geom import BALL as B, S, So, D, soft, finish
from beadjoint.charset import raw_p
from beadjoint.verify import check_glyph
from beadjoint.glyphs import pieces
import acute

loop = So((1.5, -3), (5.5, -3), (5.5, 1), (1.5, 1))
V = {
    "cur": raw_p()["&"],
    # A: bowl's right arm stops short (ball at y=6.5), tail steeper from the loop corner
    "A": loop | S((3.5, 1), (1, 3.5, 1), (1, 9), (6, 9), (6, 6.5, B)) | S((4.5, 1), (9, 10)),
    # B: no right arm: bowl ends on the baseline, tail crosses the bowl's end
    "B": loop | S((3.5, 1), (1, 3.5, 1), (1, 9), (6.5, 9, B)) | S((4.5, 1), (9, 10)),
    # C: tail crosses the right arm square-on: arm leans right, tail from the loop to the baseline
    "C": loop | S((3.5, 1), (1, 3.5, 1), (1, 9), (5, 9), (8.5, 4.5, B)) | S((4.5, 1), (9, 10)),
}
SC = 30
im = Image.new("RGB", (len(V) * 14 * SC, 18 * SC), (250, 249, 246))
d = ImageDraw.Draw(im)
for i, (k, raw) in enumerate(V.items()):
    ox, oy = i * 14 * SC + 2 * SC, 6 * SC
    fin = acute.finish_acute(raw) if k != "cur" else finish(raw)
    for g, col in ((fin, (200, 90, 60)), (soft(raw), (28, 30, 36))):
        for p in pieces(g):
            d.polygon([(ox + x * SC, oy + y * SC) for x, y in p.exterior.coords], fill=col)
            for h in p.interiors:
                d.polygon([(ox + x * SC, oy + y * SC) for x, y in h.coords], fill=(250, 249, 246))
    r = check_glyph(fin)
    d.text((ox, oy + 12 * SC), f"& {k}  max {r['thickness']:.2f}w  thin {len(r['thin'])} isl {len(r['islands'])}", fill=(0, 0, 0))
    print(k, r["thickness"], r["at"], r["thin"], r["islands"])
im.save(str(Path(__file__).resolve().parents[2] / "review/frodo-r3/amp.png"))
