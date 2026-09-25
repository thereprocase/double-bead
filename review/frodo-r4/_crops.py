"""Frodo r4: trouble strings large: Tab (engine), proportional (engine), Tab TTF without kerning."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r4"))
from beadjoint.setting import mixed, kerned
from beadjoint.specimen import draw_rows
from _nokern import nk
R = str(Path(__file__).resolve().parents[2] / "review/frodo-r4")
S = ['1-1/8" - 1-13/32"', '#8-32  12-A  1/4-20', 'G1/4"  24V  Ø12 H7', '0.25 mm²  3.2 µF', '(typ.)  e-mail  a_b_c',
     'M14  17 mm  147  M10  1117', '7/8"  Tj  To  x2 ×2']
def sp(s):  # engine collapses runs of spaces; set double-spaced chunks as separate words via one space
    return s.replace("  ", " ")
rows = [("Tab engine", [mixed(sp(s)) for s in S]), ("P engine (proportional figures)", [kerned(sp(s)) for s in S]),
        ("Tab TTF, no kerning", [nk.layout(sp(s)) for s in S])]
draw_rows(rows, scale=7, path=R + r"\crops_now.png")
print("ok")
