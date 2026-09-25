import sys
from pathlib import Path; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.glyphs import _raw_p
from beadjoint.geom import widen, finish, S, BALL as B
from beadjoint.verify import check_glyph
from beadjoint.specimen import draw_rows
from beadjoint.setting import tabular
from beadjoint.charset import full_m, MONO_MAX

raw0 = _raw_p()["0"]
widened0 = widen(raw0)
x0, y0, x1, y1 = widened0.bounds
print("widened ring bounds:", round(x0,3), round(y0,3), round(x1,3), round(y1,3))

# stub slash near opposite corners, mirroring the ø technique but scaled for a 9w-wide 12w-tall ring
stub1 = S((x1 - 1.6, 1.4), (x1 + 0.35, -0.6, B))     # inside near top-right corner, poking out top-right
stub2 = S((x0 + 1.6, 7.6), (x0 - 0.35, 9.6, B))      # inside near bottom-left corner, poking out bottom-left
candidate = finish(widened0 | stub1 | stub2)
b = candidate.bounds
print("candidate bounds:", [round(v,3) for v in b], "width", round(b[2]-b[0],3), "MONO_MAX", MONO_MAX)
result = check_glyph(candidate)
print("check_glyph:", result)

m = dict(full_m())
m["0"] = type(m["O"])("0", "M:0", candidate)
draw_rows([("slashed-zero candidate vs O", [tabular("0O0O", glyphs=m)])], scale=24,
          path=str(Path(__file__).resolve().parents[2] / "review/frodo-r6/slash_zero.png"))
