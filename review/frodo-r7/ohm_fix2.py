import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageFilter
from beadjoint.geom import S, BALL as B, finish
from beadjoint.glyphs import Glyph
from beadjoint.setting import mixed
from beadjoint import charset
from beadjoint.specimen import draw_rows
from beadjoint.verify import check_glyph

R = str(Path(__file__).resolve().parents[2] / "review/frodo-r7")

cands = {
    "old":  S((-0.5, 9, B), (1.5, 7, 1.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 7, 1.5), (8.5, 9, B)),
    "v2":   S((-1.5, 9, B), (1.5, 5, 2.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 5, 2.5), (9.5, 9, B)),
    "v3":   S((-2.5, 9, B), (1.5, 3, 3.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 3, 3.5), (10.5, 9, B)),
}
geoms = {}
for name, raw in cands.items():
    f = finish(raw)
    chk = check_glyph(f)
    print(name, "ok" if chk["ok"] else "FAIL", chk["thin"], chk["islands"], "two_bead", chk["two_bead"], "bounds", f.bounds)
    geoms[name] = f

rows_txt = []
for name in cands:
    glyphs = dict(charset.full_p())
    glyphs["Ω"] = Glyph("Ω", f"P:Ω-{name}", geoms[name])
    rows_txt.append(mixed("10kΩ ±5%", glyphs))

rows = [("10kΩ ±5%: old / v2 / v3", rows_txt)]
SCALE = 3
sim_rows = [(cap, [[(c, g.buffer(0.3), x) for c, g, x in ln] for ln in lines]) for cap, lines in rows]
draw_rows(sim_rows, scale=SCALE, path=R + r"\ohm_fix2_raw.png")
img = Image.open(R + r"\ohm_fix2_raw.png")
img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
img.filter(ImageFilter.GaussianBlur(radius=SCALE * 0.35 * 4)).save(R + r"\ohm_fix2_blur.png")
print("ok")
