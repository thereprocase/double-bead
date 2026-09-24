"""Frodo r3: compare analyze.py runs: body-colour specks (through-voids), wide voids, thin beads, bleed."""
import json, sys
from pathlib import Path
D = Path("/mnt/f/code/beadjoint/review/frodo-r3")
for f in sorted(D.glob("an-*.json")):
    if f.stem in ("an-full", "an-test"):
        continue
    a = json.loads(f.read_text(encoding="utf-8"))
    r = {}
    for face in ("top", "bottom"):
        v = [e[face] for e in a.values()]
        r[face] = (sum(x["speck"] for x in v), max(x["speck"] for x in v), sum(x["void_w"] for x in v),
                   sum(x["thin_len"] for x in v), max(x["bleed_max"] for x in v), sum(1 for x in v if x["bleed_max"] > 0.085))
    print(f"{f.stem[3:]:12s} " + " || ".join(
        f"{k[0]}: speck sum {s:.3f} max {m:.3f} | void {vw:.3f} | thin {t:5.2f} mm | bleed max {b:.2f} n>0.085 {n}" for k, (s, m, vw, t, b, n) in r.items()))
