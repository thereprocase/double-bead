import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_m
from beadjoint.setting import tabular
from beadjoint.specimen import draw_rows

rows = [("0 vs O vs Q vs D", [tabular("0OQD")])]
draw_rows(rows, scale=24, path=r"F:\code\beadjoint\review\frodo-r6\zero_o.png")

m = full_m()
for c in "0OQD":
    g = m[c]
    print(c, "bounds", [round(v,3) for v in g.bounds], "width", round(g.width,3))
