import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fontTools.ttLib import TTFont
f = TTFont(str(Path(__file__).resolve().parents[2] / "fonts/BeadjointTab-Regular.ttf"))
cm = f.getBestCmap()
want = {"NBSP": 0xA0, "thin sp": 0x2009, "narrow nbsp": 0x202F, "figure sp": 0x2007, "punct sp": 0x2008, "en sp": 0x2002,
        "micro": 0xB5, "greek mu": 0x3BC, "Omega": 0x3A9, "ohm": 0x2126, "diameter": 0x2300, "1/8": 0x215B, "3/8": 0x215C,
        "5/8": 0x215D, "7/8": 0x215E, "1/3": 0x2153, "larr": 0x2190, "uarr": 0x2191, "rarr": 0x2192, "darr": 0x2193,
        "le": 0x2264, "ge": 0x2265, "approx": 0x2248, "ne": 0x2260, "minus": 0x2212, "times": 0xD7, "deg": 0xB0,
        "prime": 0x2032, "dprime": 0x2033, "frac slash": 0x2044, "numero": 0x2116, "delta": 0x394, "sup2": 0xB2,
        "sup3": 0xB3, "en dash": 0x2013, "nb hyphen": 0x2011, "hyphen": 0x2010, "soft hyphen": 0xAD, "celsius": 0x2103}
for k, v in want.items():
    print(f"{k:12} U+{v:04X} {chr(v)!r:6} -> {cm.get(v)}  adv={f['hmtx'].metrics[cm[v]][0] if v in cm else '-'}")
print("space adv", f["hmtx"].metrics["space"])
