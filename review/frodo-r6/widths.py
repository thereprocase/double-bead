import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_m, full_p, CHARS, MONO_MAX

p = full_p()
for c in ["W", "Ŵ", "Æ", "æ", "Ø", "ø", "«", "»"]:
    g = p[c]
    print(f"{c!r:>6}  width={g.width:.6f}w  over_by={g.width-MONO_MAX:.6f}")
