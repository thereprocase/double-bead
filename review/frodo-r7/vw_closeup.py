import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from PIL import Image, ImageFilter
from beadjoint.setting import kerned
from beadjoint.specimen import draw_rows

R = r"F:\code\beadjoint\review\frodo-r7"
rows = [("vv w vvw wvv", [kerned("vv"), kerned("w"), kerned("vvw"), kerned("wvv")])]
SCALE = 3
sim_rows = [(cap, [[(c, g.buffer(0.3), x) for c, g, x in ln] for ln in lines]) for cap, lines in rows]
draw_rows(sim_rows, scale=SCALE, path=R + r"\vw_raw.png")
img = Image.open(R + r"\vw_raw.png")
img.filter(ImageFilter.GaussianBlur(radius=SCALE * 0.35)).save(R + r"\vw_blur.png")
print("ok")
