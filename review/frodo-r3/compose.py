"""Frodo r3: before/after contact sheet from review/frodo-r3/ba/{cur,fix}/<CP>-<face>-L<n>.png."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from PIL import Image, ImageDraw
D = Path(r"F:\code\beadjoint\review\frodo-r3\ba")
rows = [("top", "tf#&Æ", 7), ("bottom", "tf#&Æ", 1), ("bottom", "vNVk", 1)]
tiles = []
for face, chars, L in rows:
    for tag in ("cur", "fix"):
        tiles.append([(Image.open(D / tag / f"{ord(c):04X}-{face}-L{L}.png"), f"{c} {face} {tag}") for c in chars])
H = max(im.height for r in tiles for im, _ in r) + 18
W = max(sum(im.width + 10 for im, _ in r) for r in tiles)
out = Image.new("RGB", (W, H * len(tiles)), (255, 255, 255))
d = ImageDraw.Draw(out)
for i, r in enumerate(tiles):
    x = 0
    for im, lab in r:
        out.paste(im, (x, i * H))
        d.text((x + 2, i * H + im.height + 2), lab, fill=(0, 0, 0))
        x += im.width + 10
out.save(D.parent / "before-after.png")
print(out.size)
