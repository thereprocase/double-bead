import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.geom import So, finish
from beadjoint.verify import check_glyph
from beadjoint.specimen import draw_rows
from beadjoint.setting import tabular
from beadjoint.charset import full_m, MONO_MAX
from beadjoint.glyphs import Glyph

candidate = finish(So((1, -3), (7, -3), (7, 9), (1, 9)))   # narrower ring, same r=1 corners as raw '0'
b = candidate.bounds
print("candidate bounds:", [round(v,3) for v in b], "width", round(b[2]-b[0],3), "MONO_MAX", MONO_MAX)
print("check_glyph:", check_glyph(candidate))

m = dict(full_m())
m["0"] = Glyph("0", "M:0", candidate)
draw_rows([("narrower-ring zero vs O: 0O0O 0.5 100 SN00", [tabular("0O0O", glyphs=m), tabular("0.5 100 SN00", glyphs=m)])],
          scale=24, path=r"F:\code\beadjoint\review\frodo-r6\narrow_zero.png")
