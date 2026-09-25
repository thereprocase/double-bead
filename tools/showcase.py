"""Showcase images of the finished fonts, drawn from the built TTFs (kerning applied, as a shaper would).

    python tools/showcase.py        -> showcase/*.png
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beadjoint.charset import CHARS  # noqa: E402
from beadjoint.glyphs import pieces  # noqa: E402
from beadjoint.readback import FontReader  # noqa: E402

OUT = ROOT / "showcase"
BODY, INK, CAP, GUIDE = (27, 29, 32), (244, 194, 13), (143, 153, 163), (48, 52, 58)
SS = 3                                   # supersampling; polygons are drawn aliased, then downscaled
FONTS = {k: FontReader(ROOT / "fonts" / f"{k}-Regular.ttf") for k in ("Fillaprint", "FillaprintTab", "FillaprintMono")}


def ui(px, bold=False):
    for name in (("segoeuib.ttf",) if bold else ()) + ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, int(px * SS))
        except OSError:
            pass
    return ImageFont.load_default(size=int(px * SS))


def fill(d, geom, ox, oy, s):
    """geom in w, y down, baseline at y = 10; (ox, oy) is the pen origin's baseline point in final px."""
    for p in pieces(geom):
        ring = lambda r: [((ox + x * s) * SS, (oy + (y - 10) * s) * SS) for x, y in r.coords]
        d.polygon(ring(p.exterior), fill=INK)
        for h in p.interiors:
            d.polygon(ring(h), fill=BODY)


def text(d, font, s, ox, base, size_px):
    """Set s with the font at size_px per em (em = 20 w); returns the advance width in px."""
    sc = size_px / 20
    placed = FONTS[font].layout(s)
    for _, g, _ in placed:
        fill(d, g, ox, base, sc)
    return max((g.bounds[2] for _, g, _ in placed), default=0) * sc


def missing(s, font="Fillaprint"):
    return sorted({c for c in s if c != " " and ord(c) not in FONTS[font].cmap})


def canvas(w, h):
    im = Image.new("RGB", (w * SS, h * SS), BODY)
    return im, ImageDraw.Draw(im)


def save(im, name):
    OUT.mkdir(exist_ok=True)
    im = im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
    im.save(OUT / name, optimize=True)
    print(name, im.size)


def caption(d, xy, s, px=15, col=CAP, bold=False):
    d.text((xy[0] * SS, xy[1] * SS), s, fill=col, font=ui(px, bold))


def rows_image(name, title, rows, width=1800, pad=56):
    """rows: (caption, font, string, em px). Each row: caption, then the line on its own baseline."""
    y = pad + 34
    lay = []
    for cap, font, s, em in rows:
        m = missing(s, font)
        if m:
            raise SystemExit(f"{name}: {font} lacks {''.join(m)}")
        y += 26
        lay.append((cap, font, s, em, y))
        y += em * 1.05 + 30          # cap height is 0.7 em, descenders 0.2 em
    im, d = canvas(width, int(y + pad - 10))
    caption(d, (pad, pad - 8), title, 22, (230, 232, 235), bold=True)
    for cap, font, s, em, top in lay:
        caption(d, (pad, top - 8), cap, 15)
        base = top + 24 + em * 0.7 + em * 0.2    # room for accents above the cap line
        wpx = text(d, font, s, pad, base, em)
        if wpx > width - 2 * pad:
            raise SystemExit(f"{name}: '{s}' is {wpx:.0f} px wide, over {width - 2 * pad}")
    save(im, name)


def hero():
    W, pad = 1800, 64
    im, d = canvas(W, 930)
    title = "Fillaprint"
    width = max(g.bounds[2] for _, g, _ in FONTS["Fillaprint"].layout(title))
    text(d, "Fillaprint", title, pad, 250, min(280, (W - 2 * pad) * 20 / width))
    caption(d, (pad + 6, 332), "Every stroke is exactly two extrusion widths: the slicer lays it as one wall loop "
            "passing itself. No hairlines, no gap fill, no one-bead strokes.", 20, (215, 219, 223))
    lines = [("The quick brown fox jumps over the lazy dog.", 76),
             ("SPHINX OF BLACK QUARTZ, JUDGE MY VOW", 76),
             ('1/2" - 5/8" dep.   M6 × 1.0   45°   Ø12 ±0.1', 76)]
    y = 490
    for s, em in lines:
        text(d, "Fillaprint", s, pad, y, em)
        y += em * 1.4 + 6
    caption(d, (pad + 6, 890), "Set with Fillaprint-Regular.ttf v0.100, kerning from the file. Size: Fusion Height = 14 × line "
            "width (4.48 mm at 0.32 mm).", 15)
    save(im, "1-double-bead.png")


def glyph_grid():
    rd = FONTS["Fillaprint"]
    cols, cw, ch, s = 26, 70, 118, 3.2         # cell px, w -> px
    cells, col, row = [], 0, 0
    for c in CHARS:
        g = rd.outline(rd.cmap.get(ord(c), ".notdef"))
        span = max(1, -(-int((g.bounds[2] - g.bounds[0]) * s + 12) // cw))   # wide glyphs (fractions, ‰, ™) span cells
        if col + span > cols:
            col, row = 0, row + 1
        cells.append((c, g, col, row, span))
        col += span
    pad, head = 40, 64
    im, d = canvas(cols * cw + 2 * pad, (row + 1) * ch + head + pad)
    caption(d, (pad, 22), f"Fillaprint: all {len(CHARS)} characters (ASCII, Latin-1, Latin Extended-A, "
            "punctuation, fractions, arrows)", 22, (230, 232, 235), bold=True)
    lf = ui(10)
    for c, g, col, row, span in cells:
        gx, gy, w = pad + col * cw, head + row * ch, span * cw
        base = gy + 13 * s + 10 * s                 # y = 0 sits 13 w below the cell top; baseline at y = 10
        for yl in (-4, 0, 10):
            yy = (base + (yl - 10) * s) * SS
            d.line([((gx + 3) * SS, yy), ((gx + w - 3) * SS, yy)], fill=GUIDE, width=SS)
        x0, _, x1, _ = g.bounds
        fill(d, g, gx + (w - (x1 - x0) * s) / 2 - x0 * s, base, s)
        d.text(((gx + 4) * SS, (gy + ch - 16) * SS), f"{ord(c):04X}", fill=CAP, font=lf)
    save(im, "2-all-glyphs.png")


def languages():
    rows = [("Czech", "Příliš žluťoučký kůň úpěl ďábelské ódy"),
            ("Polish", "Zażółć gęślą jaźń. Pchnąć w tę łódź jeża"),
            ("German", "Falsches Üben von Xylophonmusik quält jeden größeren Zwerg. GROẞE"),
            ("French", "Voix ambiguë d’un cœur qui au zéphyr préfère les jattes de kiwis"),
            ("Spanish", "Jovencillo emponzoñado de whisky: ¡qué figurota exhibe!"),
            ("Portuguese", "À noite, vovô Kowalsky vê o ímã cair no pé do pinguim"),
            ("Danish / Norwegian", "Høj bly gom vandt fræk sexquiz på wc. Blåbærsyltetøy"),
            ("Swedish / Finnish", "Flygande bäckasiner söka hwila på mjuka tuvor. Törkeä öylätti"),
            ("Icelandic", "Kæmi ný öxi hér, ykist þjófum nú bæði víl og ádrepa"),
            ("Hungarian", "Árvíztűrő tükörfúrógép"),
            ("Romanian", "Înjurând pițigăiat, zoofobul comandă vexat whisky și tequila"),
            ("Turkish", "Pijamalı hasta yağız şoföre çabucak güvendi"),
            ("Latvian / Lithuanian", "Glāžšķūņa rūķīši dzērumā čiepj Baha koncertflīģeļu vākus. Įlinkdama špaga"),
            ("Croatian / Slovenian / Maltese / Esperanto", "Đače, Češće, ŽIVIO! Ħ ċ ġ ż. Eĥoŝanĝo ĉiuĵaŭde"),
            ("Welsh", "Parciais fy jac codi baw hud llawn dŵr ger tŷ Mabon. Ẁ ẁ Ẃ ẃ Ẅ ẅ Ỳ ỳ"),
            ("Catalan", "Jove xef, porti whisky amb quinze glaçons d’hidrogen, coi!")]
    rows_image("3-languages.png", "Accents: Latin-1 and Latin Extended-A, every language that uses them",
               [(c, "Fillaprint", s, 50) for c, s in rows])


def symbols():
    rows = [("ASCII punctuation and symbols", "Fillaprint", "! \" # $ % & ' ( ) * + , - . / : ; < = > ? @ [ \\ ] ^ _ ` { | } ~", 60),
            ("Latin-1 symbols", "Fillaprint", "¡ ¢ £ ¤ ¥ ¦ § ¨ © ª « ¬ ® ¯ ° ± ² ³ ´ µ ¶ · ¸ ¹ º » ¼ ½ ¾ ¿ × ÷", 60),
            ("Typographic punctuation", "Fillaprint", "– — ‘ ’ ‚ “ ” „ † ‡ • … ‰ ‹ › ⁄ € ™ ′ ″ −", 60),
            ("Maths, fractions, arrows", "Fillaprint", "Ω ⅓ ⅔ ⅛ ⅜ ⅝ ⅞ ← ↑ → ↓ ≤ ≥ ≈ ≠ ± × ÷ ° ¬ ƒ ₺", 60),
            ("Figures, Fillaprint: proportional, for labels", "Fillaprint", "0123456789  3/16\"  11/32\"  1-1/8\"", 60),
            ("Figures, Fillaprint Tab: every figure one width, for columns", "FillaprintTab", "0123456789  3/16\"  11/32\"  1-1/8\"", 60)]
    rows_image("4-symbols.png", "Keyboard symbols, punctuation and figures", rows)


def advance(font, s):
    rd, pen, prev = FONTS[font], 0.0, None
    for ch in s:
        name = rd.cmap.get(ord(ch), ".notdef")
        pen += (rd.pair(prev, name) if prev else 0) / 50 + rd.hmtx[name][0] / 50
        prev = name
    return pen


def families():
    W, pad, em = 1800, 56, 60
    im, d = canvas(W, 1400)
    caption(d, (pad, pad - 8), "Three fonts: Fillaprint, Fillaprint Tab, Fillaprint Mono", 22, (230, 232, 235), bold=True)
    y = pad + 60
    caption(d, (pad, y - 8), "Fillaprint: proportional, for labels", 15)
    text(d, "Fillaprint", 'Masonry 1/2" - 5/8" dep.  Hex 4 mm  Torx T25', pad, y + 24 + em * 0.9, em)
    y += 24 + em * 1.1 + 40
    values = ["6.35", "8.73", "15.88", "111.11", "20.64", "1.00"]
    for i, (font, cap) in enumerate((("Fillaprint", "Fillaprint: figures vary in width, so a right-aligned column wobbles"),
                                     ("FillaprintTab", "Fillaprint Tab: every figure 9 w wide, so the points line up"))):
        x = pad + i * 820
        caption(d, (x, y - 8), cap, 15)
        right = x + 330
        for j, v in enumerate(values):
            text(d, font, v + " mm", right - advance(font, v) * em / 20, y + 24 + em * 0.75 + j * em * 1.05, em)
    y += 24 + len(values) * em * 1.05 + 50
    caption(d, (pad, y - 8), "Fillaprint Mono: every glyph on one 12 w cell", 15)
    text(d, "FillaprintMono", "if (x != 7) { y = a[i] * 2; }", pad, y + 24 + em * 0.75, em)
    y += 24 + em * 1.0 + pad
    im = im.crop((0, 0, im.width, int(y * SS)))
    save(im, "5-families.png")


def printed():
    """Slice crops from the demo coupon (site/dist/crops): real Orca Arachne toolpaths, top face."""
    pick = "BagR&Ø%ßŁ§@5"
    crops = [Image.open(ROOT / "site/dist/crops" / f"{ord(c):04X}-top.png").convert("RGB") for c in pick]
    cw = 300
    tiles = [c.resize((cw, int(c.height * cw / c.width)), Image.LANCZOS) for c in crops]
    th = max(t.height for t in tiles)
    cols, pad, head = 6, 24, 70
    rows = (len(tiles) + cols - 1) // cols
    im = Image.new("RGB", (cols * cw + (cols + 1) * pad, head + rows * (th + pad + 26) + pad), BODY)
    d = ImageDraw.Draw(im)
    d.text((pad, 20), "Sliced: Orca Arachne toolpaths at 0.32 mm, top face of the demo coupon "
           "(yellow = colour beads, grey = body beads, blue = design outline, white = no bead on this layer)", fill=(230, 232, 235),
           font=ImageFont.truetype("segoeuib.ttf", 20))
    for i, (c, t) in enumerate(zip(pick, tiles)):
        x = pad + (i % cols) * (cw + pad)
        y = head + (i // cols) * (th + pad + 26)
        im.paste(t, (x, y))
        d.text((x, y + t.height + 4), f"{c}  U+{ord(c):04X}", fill=CAP, font=ImageFont.truetype("segoeui.ttf", 15))
    OUT.mkdir(exist_ok=True)
    im.save(OUT / "6-sliced.png", optimize=True)
    print("6-sliced.png", im.size)


if __name__ == "__main__":
    h = FONTS["Fillaprint"].outline(FONTS["Fillaprint"].cmap[ord("H")]).bounds
    assert abs(h[1] + 4) < 0.05 and abs(h[3] - 10) < 0.05, h   # cap line -4, baseline 10
    hero(); glyph_grid(); languages(); symbols(); families(); printed()
