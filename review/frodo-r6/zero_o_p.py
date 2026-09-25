import sys
from pathlib import Path; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p
from beadjoint.setting import kerned
from beadjoint.specimen import draw_rows

rows = [("P: 0 vs O", [kerned("0O")])]
draw_rows(rows, scale=24, path=str(Path(__file__).resolve().parents[2] / "review/frodo-r6/zero_o_p.png"))
p = full_p()
for c in "0O":
    g = p[c]
    print(c, "bounds", [round(v,3) for v in g.bounds], "width", round(g.width,3))
