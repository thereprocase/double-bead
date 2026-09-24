"""Frodo r4: how far P's figure runs drift from tabular widths, and where Tab opens holes."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
import itertools
import numpy as np
from beadjoint.setting import mixed, kerned, ink_extent

def width(line):
    lo, hi = ink_extent(line)
    return hi - lo

for n in (2, 3):
    wp, wt = {}, {}
    for t in itertools.product("0123456789", repeat=n):
        s = "".join(t)
        if n == 3 and not (s[0] in "1234" ):   # keep it quick
            continue
        wp[s], wt[s] = width(kerned(s)), width(mixed(s))
    p = np.array(list(wp.values())); q = np.array(list(wt.values()))
    print(f"{n}-digit ink width  P: {p.min():.2f}..{p.max():.2f} (spread {p.max()-p.min():.2f} w)   "
          f"Tab: {q.min():.2f}..{q.max():.2f} (spread {q.max()-q.min():.2f} w)")
    print("   P narrowest:", sorted(wp, key=wp.get)[:6], " widest:", sorted(wp, key=wp.get)[-4:])
    print("   Tab narrowest:", sorted(wt, key=wt.get)[:6], " widest:", sorted(wt, key=wt.get)[-4:])
# alignment of the last figure's right edge in a stacked, right-aligned list (what Tab is for)
lst = ["6", "8", "10", "11", "12", "14", "16", "17", "20", "25", "30", "40"]
print("right-aligned list, left ink edge offset from widest (w):")
for f in (kerned, mixed):
    ws = {s: width(f(s)) for s in lst}
    m = max(ws.values())
    print(f"  {f.__name__:6}", " ".join(f"{s}:{m - w:.1f}" for s, w in ws.items()))
