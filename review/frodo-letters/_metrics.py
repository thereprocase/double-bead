import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from fontTools.ttLib import TTFont
f = TTFont(str(Path(__file__).resolve().parents[2] / "fonts/Beadjoint-Regular.ttf"))
h, o, head = f["hhea"], f["OS/2"], f["head"]
print("hhea asc/desc/gap", h.ascent, h.descent, h.lineGap, "| win asc/desc", o.usWinAscent, o.usWinDescent, "| head yMin/yMax", head.yMin, head.yMax)
glyf = f["glyf"]; cmap = f.getBestCmap()
over = []
for cp, name in cmap.items():
    g = glyf[name]
    if g.numberOfContours and (g.yMax > o.usWinAscent or g.yMin < -o.usWinDescent):
        over.append((chr(cp), g.yMin, g.yMax))
print(len(over), "glyphs outside usWin:", "".join(c for c, _, _ in over))
print("tallest", sorted(over, key=lambda t: -t[2])[:5], "deepest", sorted(over, key=lambda t: t[1])[:5])
print("cmap size", len(cmap), "has Á:", 0xC1 in cmap)
