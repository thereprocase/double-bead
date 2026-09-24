import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from PIL import Image, ImageFilter
from beadjoint.geom import S, BALL as B, finish, solve
from beadjoint.glyphs import Glyph
from beadjoint.setting import kerned
from beadjoint import charset
from beadjoint.specimen import draw_rows
from beadjoint.verify import check_glyph

R = r"F:\code\beadjoint\review\frodo-r7"

old = solve(lambda vy: S((1, 1, B), (3.125, vy), (5.25, 3.5), (7.375, vy), (9.5, 1, B)))
# v2: raise the middle peak from y=3.5 to y=1.6 (near the top), closing most of the notch so w
# reads as one bridged glyph instead of two v-shaped gaps
new = solve(lambda vy: S((1, 1, B), (3.125, vy), (5.25, 1.6), (7.375, vy), (9.5, 1, B)))

for name, raw in (("old", old), ("new", new)):
    f = finish(raw)
    chk = check_glyph(f)
    print(name, "ok" if chk["ok"] else "FAIL", chk["thin"], chk["islands"], "two_bead", chk["two_bead"])

glyphs_old = dict(charset.full_p())
glyphs_new = dict(charset.full_p())
glyphs_new["w"] = Glyph("w", "P:w-fix", finish(new))

rows = [("vv w vvw wvv: old w (top) / raised-peak w (bottom)",
         [kerned("vv"), kerned("w", glyphs_old), kerned("vvw", glyphs_old), kerned("wvv", glyphs_old),
          kerned("w", glyphs_new), kerned("vvw", glyphs_new), kerned("wvv", glyphs_new)])]
SCALE = 3
sim_rows = [(cap, [[(c, g.buffer(0.3), x) for c, g, x in ln] for ln in lines]) for cap, lines in rows]
draw_rows(sim_rows, scale=SCALE, path=R + r"\w_fix_raw.png")
img = Image.open(R + r"\w_fix_raw.png")
img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
img.filter(ImageFilter.GaussianBlur(radius=SCALE * 0.35 * 4)).save(R + r"\w_fix_blur.png")
print("ok")
