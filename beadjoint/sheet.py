"""Glyph sheets: every glyph of a set in a labelled grid, drawn on its guide lines."""
from PIL import Image, ImageDraw, ImageFont

from .glyphs import pieces

BG, INK, GUIDE, LABEL = (250, 249, 246), (28, 30, 36), (214, 220, 232), (120, 124, 134)


def _font(size):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def draw_glyph(d, geom, ox, oy, scale, ink=INK):
    for p in pieces(geom):
        ring = lambda r: [(ox + x * scale, oy + y * scale) for x, y in r.coords]
        d.polygon(ring(p.exterior), fill=ink)
        for h in p.interiors:
            d.polygon(ring(h), fill=BG)


def grid(glyphs, path, cols=20, scale=6, cell=(20, 34)):
    """Cells are cell[0] x cell[1] w; guide lines at the cap line (-4), x-height (0), baseline (10)."""
    chars = list(glyphs)
    rows = (len(chars) + cols - 1) // cols
    cw, ch = cell[0] * scale, cell[1] * scale
    im = Image.new("RGB", (cols * cw, rows * ch), BG)
    d = ImageDraw.Draw(im)
    f = _font(max(11, scale * 2))
    for i, c in enumerate(chars):
        gx, gy = (i % cols) * cw, (i // cols) * ch
        top = gy + 13 * scale                     # y = 0 sits 13w below the cell top (capital accents reach -12)
        for yl in (-4, 0, 10):
            d.line([(gx + 2, top + yl * scale), (gx + cw - 2, top + yl * scale)], fill=GUIDE, width=1)
        g = glyphs[c].geom
        x0, _, x1, _ = g.bounds
        draw_glyph(d, g, gx + (cw - (x1 - x0) * scale) / 2 - x0 * scale, top, scale)
        d.text((gx + 4, gy + ch - 3 * scale), f"{c} {ord(c):04X}" if len(c) == 1 else c, fill=LABEL, font=f)
    im.save(path)
    return im.size
