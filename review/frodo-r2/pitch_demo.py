"""Two-line labels at the documented 20w pitch vs 28w: accents on line 2 run into line 1."""
from _lib import *
from PIL import Image, ImageDraw
from beadjoint.specimen import BG, INK, CAPTION, _font

G = full_mixed()
HOT = (235, 70, 60)


def block(lines, pitch, scale):
    set_lines = [mixed(t, G) for t in lines]
    width = max(max(g.bounds[2] for _, g, _ in ln) for ln in set_lines)
    return set_lines, width


def draw(blocks, scale, path, margin=30):
    """blocks: [(caption, [text lines], pitch)]; ink closer than 2w to the other line is drawn red."""
    f = _font(max(14, int(scale * 1.8)))
    h, w, lay = margin, 0, []
    for cap, lines, pitch in blocks:
        sl, wd = block(lines, pitch, scale)
        lay.append((cap, sl, pitch, h))
        w = max(w, wd * scale)
        h += int(scale * 3) + int((len(lines) - 1) * pitch * scale + 32 * scale)
    im = Image.new("RGB", (int(w + 2 * margin), int(h + margin)), BG)
    d = ImageDraw.Draw(im)
    for cap, sl, pitch, top in lay:
        d.text((margin, top), cap, fill=CAPTION, font=f)
        placed = [unary_union([shift(g, 0, i * pitch) for _, g, _ in ln]) for i, ln in enumerate(sl)]
        for i, ln in enumerate(sl):
            y0 = top + scale * 3 + 12 * scale
            other = unary_union([p for j, p in enumerate(placed) if j != i])
            for _, g, _ in ln:
                g2 = shift(g, 0, i * pitch)
                bad = g2.intersection(other.buffer(2.0)) if not other.is_empty else None
                for geom, col in ((g2, INK), (bad, HOT)):
                    if geom is None or geom.is_empty:
                        continue
                    for p in pieces(geom) if geom.geom_type in ("Polygon", "MultiPolygon") else []:
                        ring = lambda r: [(margin + x * scale, y0 + y * scale) for x, y in r.coords]
                        d.polygon(ring(p.exterior), fill=col)
                        for hh in p.interiors:
                            d.polygon(ring(hh), fill=BG)
        for i in range(len(sl) - 1):
            print(cap, "line", i, "->", i + 1, "min distance", round(placed[i].distance(placed[i + 1]), 2))
    im.save(fr"{R}\{path}")


lines = ["Schrauben M6 gjpq", "ÄRMEL Öl Ångström", "Ďábel Ťukot ÚČET", "Şoför Ņina Ģirts"]
draw([("20 w pitch (fonts and README today): red = closer than 2 w to the other line", lines, 20.0),
      ("28 w pitch (proposed lineGap 400)", lines, 28.0)], scale=6, path="pitch_demo.png")
