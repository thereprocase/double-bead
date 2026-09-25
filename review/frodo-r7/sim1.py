"""Frodo r7: legibility at print size. Render confusable groups + real labels at print scale (3 px/w),
plain and print-simulated (ink grown 0.3w to mimic colour bleed, then Gaussian blur ~1px for squish/AA)."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageFilter
from beadjoint.setting import kerned, mixed
from beadjoint.specimen import draw_rows

R = str(Path(__file__).resolve().parents[2] / "review/frodo-r7")

# groups: (caption, text, use_mixed)
GROUPS = [
    ("0 O D Q", "0 O D Q  0O 0Q OQ DO", False),
    ("1 l I | !", "1 l I | !  1l lI Il l1", False),
    ("5 S", "5 S  5S S5", False),
    ("8 B", "8 B  8B B8", False),
    ("2 Z", "2 Z  2Z Z2", False),
    ("6 G b", "6 G b  6G Gb 6b", False),
    ("9 g q", "9 g q  9g gq 9q", False),
    ("rn m", "rn m  rnm mrn", False),
    ("cl d", "cl d  cld dcl", False),
    ("vv w", "vv w  vvw wvv", False),
    ("u v", "u v  uv vu", False),
    ("n h", "n h  nh hn", False),
    ("c e o", "c e o  ceo oec", False),
    ("i j", "i j  ij ji", False),
    ("punct : ; , . ' \" ″ \u2018 \u2019 \u201c \u201d", ": ; , . ' \" \u2033 \u2018 \u2019 \u201c \u201d", False),
    ("dashes - \u2013 \u2014 \u2212", "- \u2013 \u2014 \u2212  a-b a\u2013b a\u2014b a\u2212b", False),
    ("x \u00d7", "x \u00d7  2x2 2\u00d72", False),
    ("a \u00aa", "a \u00aa  1a 1\u00aa", False),
    ("o \u00ba \u00b0", "o \u00ba \u00b0  10o 10\u00ba 10\u00b0", False),
]

LABELS = [
    "SN 0O1Il5S8B",
    "M6 x 1.0",
    "BIN 12-A",
    "\u00d812 H7",
    "10k\u03a9 \u00b15%",
    "\u00bd\" - \u215d\"",
]

rows = []
for cap, text, use_mixed in GROUPS:
    line = mixed(text) if use_mixed else kerned(text)
    rows.append((cap, [line]))
rows.append(("mixed labels", [mixed(s) for s in LABELS]))

SCALE = 3

# plain, at print scale
draw_rows(rows, scale=SCALE, path=R + r"\plain.png")

# print-simulated: grow every glyph's ink 0.3w (colour bleed), then blur the raster (squish/AA)
sim_rows = [(cap, [[(c, g.buffer(0.3), x) for c, g, x in ln] for ln in lines]) for cap, lines in rows]
im = draw_rows(sim_rows, scale=SCALE, path=R + r"\sim_raw.png")
from PIL import Image
img = Image.open(R + r"\sim_raw.png")
img.filter(ImageFilter.GaussianBlur(radius=SCALE * 0.35)).save(R + r"\sim_blur.png")
print("ok", im)
