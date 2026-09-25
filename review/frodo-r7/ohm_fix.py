import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageFilter
from shapely import affinity
from beadjoint.geom import S, BALL as B, finish
from beadjoint.verify import check_glyph
from beadjoint.setting import kerned
from beadjoint.charset import full_p
from beadjoint.specimen import draw_rows

R = str(Path(__file__).resolve().parents[2] / "review/frodo-r7")

# current Ω (latin.py:232)
old = S((-0.5, 9, B), (1.5, 7, 1.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 7, 1.5), (8.5, 9, B))
old_f = finish(old)
print("old check", check_glyph(old_f))
print("old bounds", old_f.bounds)

# candidate: wider, lower flare so the curl survives blur/dilation
new = S((-1.5, 9, B), (1.5, 5, 2.5), (1.5, -3, 2), (6.5, -3, 2), (6.5, 5, 2.5), (9.5, 9, B))
new_f = finish(new)
print("new check", check_glyph(new_f))
print("new bounds", new_f.bounds)

p = full_p()
n_g = p["n"].geom

def line(g, x=0.0):
    return [("g", affinity.translate(g, x), x)]

rows = [("n / old omega / new omega", [line(n_g), line(old_f, 12), line(new_f, 24)])]
SCALE = 3
sim_rows = [(cap, [[(c, g.buffer(0.3), x) for c, g, x in ln] for ln in lines]) for cap, lines in rows]
draw_rows(sim_rows, scale=SCALE, path=R + r"\ohm_fix_raw.png")
img = Image.open(R + r"\ohm_fix_raw.png")
img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
img.filter(ImageFilter.GaussianBlur(radius=SCALE * 0.35 * 4)).save(R + r"\ohm_fix_blur.png")
print("ok")
