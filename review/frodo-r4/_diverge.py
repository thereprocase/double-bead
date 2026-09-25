"""Frodo r4: engine (mixed / kerned) vs TTF (Tab / proportional) per pair, label by label."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.setting import mixed, kerned
from beadjoint.readback import FontReader

LABELS = ['1/4" Jt.', '1/2" - 5/8" dep.', '5/16" Jt.', '5/8" - 25/32" dep.', '9/16" Jt.', '1-1/8" - 1-13/32" dep.',
          '7/8" Jt.', '1-3/4" - 2-3/16" dep.',
          "M3 x 8 SHCS", "M4 x 12 BHCS", "#8-32 x 1/2\"", "1/4-20 NUT", "BIN 12-A", "Resistors 10k-47k",
          "WAGO 221-413", "Zip ties 200 mm", "SPARE FUSES 5A",
          "24V DC", "120V~ 15A", "L1 L2 L3 N PE", "+5V GND", "IN / OUT", "OFF - ON", "HOT", "G1/4\" BSPP",
          "NPT 3/8\"", "Max 6 bar",
          "45°", "±0.1 mm", "Ø12 H7", "0.25 mm²", "3.2 µF", "100% (typ.)", "2026-09-23", "12:30", "x2 ×2",
          "1:50", "R2.5", "#3 PH", "T25 Torx", "No. 4", "½ ¼ ¾",
          "Ventilation", "Kitchen", "Wavy", "Toyota", "LAVA", "Yawn", "AVATAR", "Fjord", "fifty", "office", "Tj", "yj",
          "\"Quote\"", "'single'", "(paren)", "[bracket]", "{brace}", "a_b_c", "e-mail", "http://pve:8080/", "C:\\temp"]

F = str(Path(__file__).resolve().parents[2] / "fonts")
tab = FontReader(F + r"\BeadjointTab-Regular.ttf")
prop = FontReader(F + r"\Beadjoint-Regular.ttf")


def gaps(line):
    """[(a, b, true distance, left-ink x of b)] for consecutive glyphs."""
    out = []
    for (ca, ga, _), (cb, gb, _) in zip(line, line[1:]):
        out.append((ca, cb, ga.distance(gb), gb.bounds[0]))
    return out


def compare(name, eng, ttf, thr=0.25):
    rows = []
    for text in LABELS:
        e, t = eng(text), ttf(text)
        e0, t0 = e[0][1].bounds[0], t[0][1].bounds[0]
        ge, gt = gaps(e), gaps(t)
        for (a, b, de, xe), (_, _, dt, xt) in zip(ge, gt):
            # change in b's left-ink position relative to a (TTF minus engine), and the true distances
            rows.append((text, a, b, de, dt))
        we = e[-1][1].bounds[2] - e0
        wt = t[-1][1].bounds[2] - t0
        if abs(we - wt) > 0.5:
            print(f"{name} WIDTH {text!r}: engine {we:.2f} ttf {wt:.2f} ({wt - we:+.2f})")
    print(f"--- {name}: pairs whose true gap differs by > {thr} w (engine -> ttf)")
    seen = set()
    for text, a, b, de, dt in rows:
        if abs(dt - de) > thr and (a, b) not in seen:
            seen.add((a, b))
            print(f"  {text!r:28} {a}{b}: {de:.2f} -> {dt:.2f} ({dt - de:+.2f})")


if __name__ == "__main__":
    compare("Tab", mixed, tab.layout, 0.08)
    compare("Prop", kerned, prop.layout, 0.08)
