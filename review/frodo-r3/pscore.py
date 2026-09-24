"""Frodo r3: score prototype slices (review/frodo-r3/sl/an-<tag>.json) given on the command line."""
import json, sys
from pathlib import Path
D = Path("/mnt/f/code/beadjoint/review/frodo-r3/sl")
for tag in sys.argv[1:]:
    a = json.loads((D / f"an-{tag}.json").read_text(encoding="utf-8"))
    out = []
    for face in ("top", "bottom"):
        v = [e[face] for e in a.values()]
        back = "6" if face == "top" else "2"
        out.append(f"{face[0]}: speck sum {sum(x['speck'] for x in v):.3f} max {max(x['speck'] for x in v):.3f} | "
                   f"back-layer void sum {sum(x['per_layer'][back] for x in v):.3f} max {max(x['per_layer'][back] for x in v):.3f} | "
                   f"thin {sum(x['thin_len'] for x in v):5.2f} | bleed max {max(x['bleed_max'] for x in v):.2f} n>0.085 {sum(1 for x in v if x['bleed_max'] > 0.085)}")
    print(f"{tag:16s} " + " || ".join(out))
