import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from functools import lru_cache
from beadjoint.setting import mixed
import proto_setting as ps
from _ctx import render
R = str(Path(__file__).resolve().parents[2] / "review/frodo-symbols")
lines = ["The quick brown fox jumps over the lazy dog.", "les jattes de kiwis, jeden Tag, ąę jeż", "a jar, the jig; x jet (j) BIN 12-A"]
rows = [("now", [mixed(t) for t in lines]), ("rule B (descender overhang ignored)", [ps.mixed_b(t) for t in lines])]
full = ps.band_x.__wrapped__
@lru_cache(maxsize=None)
def half(g):
    l, r = full(g)
    return (l + g.minx) / 2, (r + g.maxx) / 2
ps.band_x = half
rows.append(("rule B-half (descender overhang counts 50%)", [ps.mixed_b(t) for t in lines]))
render(rows, fr"{R}\spacing_j.png", factor=2.5)
