"""Frodo r4: more real label strings, P TTF vs Tab TTF, window check on both."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.readback import FontReader
from beadjoint.specimen import draw_rows
from beadjoint.verify import line_gaps
R = r"F:\code\beadjoint\review\frodo-r4"
F = r"F:\code\beadjoint\fonts"
tab = FontReader(F + r"\BeadjointTab-Regular.ttf")
prop = FontReader(F + r"\Beadjoint-Regular.ttf")
S = ["M3×8 M3x8 M5×0.8", '3/8"-16 1/2"-13 #6-32', "10-32 UNF 1/4\" NPT", "-40°C +85°C 5°F",
     "220µF 25V 5V/2A", "AC/DC N/A L/N USB-C", "1N4148 LM7805 RJ45", "Ø3 mm 3mm 0.5A T", "WD-40 3-IN-ONE Cat.6",
     "100°C (212°F) 1,5 mm² 4×1.5"]
for name, f in (("Tab", tab), ("P", prop)):
    for s in S:
        ln = f.layout(s)
        bad = [(a, b, round(d, 2)) for a, b, d in line_gaps([(c, g) for c, g, _ in ln]) if d < 1.98]
        if bad:
            print(name, s, bad)
draw_rows([("Beadjoint Tab TTF", [tab.layout(s) for s in S[:5]]), ("", [tab.layout(s) for s in S[5:]]),
           ("Beadjoint TTF", [prop.layout(s) for s in S[:5]]), (" ", [prop.layout(s) for s in S[5:]])], scale=5, path=R + r"\more.png")
print("ok")
