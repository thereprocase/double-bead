"""Context lines with prototype glyph overrides, drawn big and small."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image
from beadjoint.geom import finish, S, D, BALL as B
from beadjoint.glyphs import Glyph
from beadjoint.charset import full_mixed
from beadjoint.setting import mixed
from beadjoint.specimen import draw_rows
from beadjoint.latin import shift, mirror_x
from beadjoint.geom import rotate180
import proto_glyphs as pg

R = str(Path(__file__).resolve().parents[2] / "review/frodo-symbols")


def with_(over, tag):
    g = dict(full_mixed())
    for c, geom in over.items():
        g[c] = Glyph(c, f"{tag}:{c}", finish(geom))
    return g


def render(rows, path, big=8, factor=3.0):
    tmp = path.replace(".png", "_big.png")
    draw_rows(rows, scale=big, path=tmp)
    im = Image.open(tmp)
    im.resize((int(im.width / factor), int(im.height / factor)), Image.LANCZOS).save(path)


def quote_set(r_single, l_single, gap=4.4):
    comma = shift(r_single, 0, 12)
    return {"’": r_single, "‘": l_single, "”": r_single | shift(r_single, gap), "“": l_single | shift(l_single, gap),
            ",": comma, "‚": comma, "„": comma | shift(comma, gap), ";": shift(D((1, 1)), 0.6) | comma}


if __name__ == "__main__":
    q = pg.quotes()
    text = "‘Jt.’ “1/2 in” it’s, „so“ a;b"
    rows = [("now", [mixed(text)])]
    for k in ("Q1 head", "Q2 bent", "Q4 mirror", "Q5 head+mirror"):
        rows.append((k, [mixed(text, with_(quote_set(q["’ " + k], q["‘ " + k]), k))]))
    render(rows, fr"{R}\quotes_ctx.png")
    st = pg.star()
    st["* 5-spoke L3.6"] = pg.top_at(pg.spokes((4.5, 0), 5, 3.6))
    text = "Jt.* 2*3 2×3 M6 x 1.0 a*b #3*"
    rows = [(k, [mixed(text, with_({"*": st[k]}, k))]) for k in
            ("* now (x-shape)", "* 3-spoke L3.2", "* 5-spoke L3.2", "* 5-spoke L3.6", "* 6-spoke L3")]
    render(rows, fr"{R}\star_ctx.png")
