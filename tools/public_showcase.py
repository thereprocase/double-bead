"""Render public specimens from the actual TTF outlines and kerning.

Run: python tools/public_showcase.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beadjoint.readback import FontReader
from beadjoint.glyphs import pieces

OUT = ROOT / "showcase"
S = 2
PAPER = "#F1EDE3"
INK = "#202C31"
MUTED = "#586566"
ACCENT = "#CE4F29"
LINE = "#CECABD"
FONTS = {name: FontReader(ROOT / "fonts" / f"{name}-Regular.ttf")
         for name in ("BrewsterTechnical", "BrewsterTechnicalTab", "BrewsterTechnicalMono")}


def ui(size, bold=False):
    for path in (["C:/Windows/Fonts/segoeuib.ttf"] if bold else []) + [
            "C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(path).exists():
            return ImageFont.truetype(path, size * S)
    return ImageFont.load_default(size=size * S)


def canvas(w, h, bg=PAPER):
    im = Image.new("RGB", (w*S, h*S), bg)
    return im, ImageDraw.Draw(im)


def label(d, x, y, value, size=23, color=MUTED, bold=False):
    font = ui(size, bold)
    bounds = d.textbbox((x*S, y*S), value, font=font)
    assert bounds[2] <= d._image.width - 25*S, value
    assert bounds[3] <= d._image.height - 20*S, value
    d.text((x*S, y*S), value, font=font, fill=color)


def line(d, coords, color=LINE, width=1):
    d.line([(x*S, y*S) for x, y in coords], fill=color, width=width*S)


def shape(d, geom, x, base, scale, color=INK, bg=PAPER):
    for polygon in pieces(geom):
        def pts(ring):
            return [((x+a*scale)*S, (base+(b-10)*scale)*S) for a,b in ring.coords]
        d.polygon(pts(polygon.exterior), fill=color)
        for ring in polygon.interiors:
            d.polygon(pts(ring), fill=bg)


def text(d, value, x, base, em, family="BrewsterTechnical", color=INK, bg=PAPER):
    reader = FONTS[family]
    missing = {c for c in value if ord(c) not in reader.cmap}
    assert not missing, missing
    for _, geom, _ in reader.layout(value):
        assert x+geom.bounds[2]*em/20 < d._image.width/S-30, value
        assert base+(geom.bounds[1]-10)*em/20 >= 0, value
        assert base+(geom.bounds[3]-10)*em/20 < d._image.height/S-20, value
        shape(d, geom, x, base, em/20, color, bg)


def save(im, name):
    OUT.mkdir(exist_ok=True)
    im.resize((im.width//S, im.height//S), Image.Resampling.LANCZOS).save(OUT/name, optimize=True)
    print(name)


def hero():
    im,d = canvas(1600,900)
    label(d,64,40,"TYPE FOR FDM PRINTING",23,ACCENT,True)
    label(d,1190,40,"THREE FONT FAMILIES",20)
    line(d,[(64,95),(1536,95)])
    title = "Brewster Technical"
    width = max(g.bounds[2] for _, g, _ in FONTS["BrewsterTechnical"].layout(title))
    text(d,title,60,338,min(248, 1470 * 20 / width))
    label(d,68,399,"Ink and negative space.",42,INK,True)
    label(d,68,463,"1:1 minimum width for strokes and gaps.",27)
    line(d,[(64,550),(1536,550)])
    text(d,'M6 × 1.0   Ø12   ±0.1   45°',64,674,94)
    for x, title, detail in [(64,"PROPORTIONAL","Everyday labels"),(580,"TABULAR FIGURES","Measurements in columns"),
                             (1096,"MONOSPACE","One fixed character width")]:
        label(d,x,768,title,21,ACCENT,True)
        label(d,x,806,detail,23,INK)
    save(im,"hero.png")


def rule():
    im,d = canvas(1600,1000)
    label(d,64,42,"THE TWO-BEAD RULE",23,ACCENT,True)
    label(d,64,92,"Design the space, too.",48,INK,True)
    reader=FONTS["BrewsterTechnical"]
    geom=reader.outline(reader.cmap[ord("H")])
    x,base,scale=100,775,34
    for gy in range(-5,12):
        line(d,[(95,base+(gy-10)*scale),(600,base+(gy-10)*scale)],LINE)
    shape(d,geom,x,base,scale)
    # Dimension the actual H scanline, including its real (larger than minimum) gap.
    segments=sorted(geom.intersection(LineString([(-100,-1),(100,-1)])).geoms,key=lambda g:g.bounds[0])
    left,right=segments
    y=850
    for a,b,caption in [(left.bounds[0],left.bounds[2],"2w"),
                         (left.bounds[2],right.bounds[0],f"{right.bounds[0]-left.bounds[2]:g}w gap")]:
        a,b=x+a*scale,x+b*scale
        line(d,[(a,y),(b,y)],ACCENT,2)
        for xx in (a,b): line(d,[(xx,y-10),(xx,y+10)],ACCENT,2)
        label(d,a,y+18,caption,22,ACCENT,True)
    label(d,740,270,"2w",78,ACCENT,True)
    label(d,740,378,"Nominal stroke width",32,INK,True)
    label(d,740,435,"Joins and crossings may be thicker.",26)
    label(d,740,545,"≥ 2w",78,ACCENT,True)
    label(d,740,653,"Minimum clear space",32,INK,True)
    label(d,740,710,"Counters, gaps, dots, and accents need room.",26)
    label(d,64,948,"w = extrusion line width  /  H outline from the released TTF  /  native design scale",22)
    save(im,"two-bead-rule.png")


def labels():
    im,d=canvas(1600,1100,INK)
    label(d,64,42,"A WORKSHOP ALPHABET",23,"#EEB566",True)
    label(d,64,94,"Labels, dimensions, and the everyday details.",37,PAPER,True)
    rows=[("TOOL LABELS",'Hex 4 mm   Torx T25',"BrewsterTechnical"),
          ("MASONRY KEYS",'1/2" Jt.   5/8" dep.',"BrewsterTechnical"),
          ("METRIC + IMPERIAL",'M6 × 1.0   3/16"   45°',"BrewsterTechnicalTab"),
          ("ACCENTS + SYMBOLS",'Façade   Maß   Ø12 ±0.1',"BrewsterTechnical"),
          ("FIXED-WIDTH LETTERING",'BIN 01   BAY 02   REV 03',"BrewsterTechnicalMono")]
    for i,(cap,value,family) in enumerate(rows):
        y=213+i*170
        label(d,64,y,cap,20,"#EEB566",True)
        text(d,value,64,y+110,95,family,PAPER,INK)
        if i<4: line(d,[(64,y+139),(1536,y+139)],"#475358")
    label(d,64,1047,"Digital specimens rendered from the font files; these are not photographs of printed parts.",22,"#C0C9C5")
    save(im,"labels.png")


if __name__ == "__main__":
    hero()
    rule()
    labels()
