import sys, traceback
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.setting import mixed, kerned
for s in ["12\u00a0mm", "12\u202fmm", "10k\u03a9", "3.2 \u03bcF", "\u2300 12", "1\u20111/8\"", "M3  x  8", " M3", "M3 ", "", "a\tb", "L1\nL2"]:
    for f in (mixed, kerned):
        try:
            ln = f(s)
            print(f"{f.__name__:6} {s!r:14} ok, {len(ln)} glyphs, chars {''.join(c for c, _, _ in ln)!r}")
        except Exception as e:
            print(f"{f.__name__:6} {s!r:14} {type(e).__name__}: {e}")
