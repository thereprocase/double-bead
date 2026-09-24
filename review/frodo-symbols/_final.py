import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.geom import finish
from beadjoint.verify import check_glyph
from beadjoint.glyphs import Glyph, pieces
from beadjoint.charset import full_mixed
from beadjoint.sheet import grid
import proto_glyphs as pg
from _ctx import with_, render
from beadjoint.setting import mixed
R = r"F:\code\beadjoint\review\frodo-symbols"
P = pg.proposals_all()
now = full_mixed()
cells = {}
for c, g in P.items():
    f = finish(g)
    r = check_glyph(f)
    b = f.bounds
    print(f"{c} T={r['thickness']:.2f} thin={r['thin']} islands={r['islands']} tight={r['tight']} "
          f"x[{b[0]:.2f},{b[2]:.2f}] y[{b[1]:.2f},{b[3]:.2f}] pcs={len(pieces(f))}")
    cells[c + " now"] = Glyph(c, c + " now", now[c].geom)
    cells[c + " new"] = Glyph(c, c + " new", f)
grid(cells, fr"{R}\proposals.png", cols=10, scale=8, cell=(26, 24))
G = with_(P, "new")
lines = ["45% 3‰ • item · x 45°C 45º", "¼\" ½\" ¾\" Jt. ¹ ² ³", "§2 §§ 5S ¬x ¤", "‘Jt.’ “1/2 in” it’s, „so“ a;b 5′ 6″ 7\"",
         "Jt.* 2*3 2×3 M6 x 1.0"]
render([("now", [mixed(t) for t in lines]), ("proposed", [mixed(t, G) for t in lines])], fr"{R}\proposals_ctx.png", factor=2.5)
