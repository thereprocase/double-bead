import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from PIL import Image, ImageFilter
from beadjoint.geom import S, BALL as B, finish
from beadjoint.glyphs import Glyph
from beadjoint.setting import mixed
from beadjoint import charset
from beadjoint.specimen import draw_rows
from beadjoint.verify import check_glyph

R = r"F:\code\beadjoint\review\frodo-r7"

new_geom = finish(S((-1.5, 9, B), (1.5, 5, 2.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 5, 2.5), (9.5, 9, B)))
assert check_glyph(new_geom)["ok"]

glyphs = dict(charset.full_p())
glyphs["Ω"] = Glyph("Ω", "P:Ω-fix", new_geom)

rows = [("10kΩ ±5% : old (top) vs fixed (bottom)", [mixed("10kΩ ±5%", charset.full_p()), mixed("10kΩ ±5%", glyphs)])]
SCALE = 3
sim_rows = [(cap, [[(c, g.buffer(0.3), x) for c, g, x in ln] for ln in lines]) for cap, lines in rows]
draw_rows(sim_rows, scale=SCALE, path=R + r"\ohm_ctx_raw.png")
img = Image.open(R + r"\ohm_ctx_raw.png")
img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
img.filter(ImageFilter.GaussianBlur(radius=SCALE * 0.35 * 4)).save(R + r"\ohm_ctx_blur.png")
print("ok")
