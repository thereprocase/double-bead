"""Specimen and thickness-map images, drawn from set lines (source geometry or read-back font)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.ops import unary_union

from .glyphs import pieces
from .verify import opening, raster

BG = (34, 36, 42)
INK = (250, 210, 60)
PITCH = 28          # line pitch in w (round 2)
CAPTION = (150, 154, 164)


def _font(size):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def draw_rows(rows, scale, path, margin=40):
    """rows: [(caption, [set line, ...])]; each set line is [(char, geom, x)], stacked PITCH w apart."""
    cap_font = _font(max(14, int(scale * 1.6)))
    height, width = margin, 0
    blocks = []
    for caption, lines in rows:
        w = max((max(g.bounds[2] for _, g, _ in ln) for ln in lines if ln), default=0)
        width = max(width, w * scale)
        blocks.append((caption, lines, height))
        height += int(scale * 2.5) + (len(lines) * PITCH + 8) * scale + int(scale * 3)
    im = Image.new("RGB", (int(width + 2 * margin), int(height + margin)), BG)
    d = ImageDraw.Draw(im)
    for caption, lines, top in blocks:
        d.text((margin, top), caption, fill=CAPTION, font=cap_font)
        for i, ln in enumerate(lines):
            y0 = top + scale * 2.5 + (i * PITCH + 13) * scale  # tallest accent (y = -12) sits 1w under the caption
            for _, g, _ in ln:
                for p in pieces(g):
                    ring = lambda r: [(margin + x * scale, y0 + y * scale) for x, y in r.coords]
                    d.polygon(ring(p.exterior), fill=INK)
                    for h in p.interiors:
                        d.polygon(ring(h), fill=BG)
    im.save(path)
    return im.size


THICK_CLASSES = [(2.2, (120, 200, 170)), (2.5, (240, 180, 60)), (2.85, (230, 60, 50))]


def thickness_map(lines, res, path, margin=1.0):
    """Ink coloured by local thickness: under 2.2w teal-grey, 2.2-2.5 green, 2.5-2.85 amber, over 2.85 red."""
    geoms = [unary_union([g for _, g, _ in ln]) for ln in lines]
    masks = []
    for gi, g in enumerate(geoms):
        m = raster(g, res, pad=margin)
        masks.append(m)
    h = sum(m.shape[0] for m in masks) + 10 * len(masks)
    w = max(m.shape[1] for m in masks)
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = BG
    y = 0
    for m in masks:
        tile = np.zeros(m.shape + (3,), np.uint8)
        tile[:] = BG
        tile[m] = (90, 110, 130)
        for t, col in THICK_CLASSES:
            tile[opening(m, t / 2 - 0.5 / res, res) & m] = col
        img[y:y + m.shape[0], :m.shape[1]] = tile
        y += m.shape[0] + 10
    Image.fromarray(img).save(path)
    return img.shape[1], img.shape[0]
