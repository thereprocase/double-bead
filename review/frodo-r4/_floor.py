"""Frodo r4: share of label pairs that sit on the GAPMIN floor, for a few optical targets T."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "review/frodo-r4"))
import numpy as np
import beadjoint.setting as st
from _diverge import LABELS

def stats():
    gs, cats = [], {"lc-lc": [], "cap/fig-any": [], "punct": []}
    for text in LABELS:
        ln = st.mixed(text)
        for (a, ga, _), (b, gb, _) in zip(ln, ln[1:]):
            d = ga.distance(gb)
            if d > 4.5:          # word spaces
                continue
            gs.append(d)
            if st._punct(st.full_mixed()[a]) or st._punct(st.full_mixed()[b]):
                cats["punct"].append(d)
            elif a.islower() and b.islower():
                cats["lc-lc"].append(d)
            else:
                cats["cap/fig-any"].append(d)
    gs = np.array(gs)
    out = f"on floor (<2.06) {100 * (gs < 2.06).mean():4.0f}%  mean {gs.mean():.2f}  "
    out += "  ".join(f"{k}: {np.mean(v):.2f} ({100 * (np.array(v) < 2.06).mean():.0f}% floor)" for k, v in cats.items())
    return out

for T in (2.4, 2.7, 3.0):
    st.T = T
    st.off.cache_clear()
    print(f"T={T}: {stats()}")
