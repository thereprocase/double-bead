import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.glyphs import _raw_p
from beadjoint.geom import widen, finish, D
from beadjoint.verify import check_glyph
from beadjoint.specimen import draw_rows

raw0 = _raw_p()["0"]
widened0 = widen(raw0)
print("widened ring bounds:", [round(v,3) for v in widened0.bounds])

candidate = finish(widened0 | D((4.5, 3), 1))
print("candidate bounds:", [round(v,3) for v in candidate.bounds], "width", round(candidate.bounds[2]-candidate.bounds[0],3))
result = check_glyph(candidate)
print("check_glyph:", result)

draw_rows([("dotted-zero candidate", [[("0", candidate, 0.0)]])], scale=30,
          path=r"F:\code\beadjoint\review\frodo-r6\dotted_zero.png")
