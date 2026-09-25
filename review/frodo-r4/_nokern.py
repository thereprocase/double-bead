"""Frodo r4: what an app that ignores kerning (advances only) gets from the Tab TTF, vs the engine."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r4"))
from beadjoint.setting import mixed
from beadjoint.readback import FontReader
from _diverge import LABELS, tab

class NoKern(FontReader):
    def pair(self, a, b):
        return 0

nk = NoKern(str(Path(__file__).resolve().parents[2] / "fonts/BeadjointTab-Regular.ttf"))
if __name__ == "__main__":
    worst = []
    for text in LABELS:
        e, t = mixed(text), nk.layout(text)
        we = e[-1][1].bounds[2] - e[0][1].bounds[0]
        wt = t[-1][1].bounds[2] - t[0][1].bounds[0]
        for (a, ga, _), (b, gb, _), (_, ta, _), (_, tb, _) in zip(e, e[1:], t, t[1:]):
            de, dt = ga.distance(gb), ta.distance(tb)
            worst.append((dt - de, text, a + b, de, dt))
        print(f"{text!r:28} width engine {we:6.2f}  no-kern {wt:6.2f}  ({100 * (wt / we - 1):+.0f}%)")
    worst.sort(reverse=True)
    seen = set()
    print("\nlargest no-kern openings (true gap engine -> no-kern):")
    for d, text, p, de, dt in worst:
        if p in seen or d < 0.8:
            continue
        seen.add(p)
        print(f"  {p!r:6} {de:.2f} -> {dt:.2f} (+{d:.2f})  in {text!r}")
    print("min no-kern gap:", min(w[4] for w in worst))
