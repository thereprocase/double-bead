import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.setting import tabular, kerned

for text in ["\u2300 25.00", "M3x0.5\u00b5", "abc\u4e2ddef"]:
    print("---", repr(text))
    try:
        tabular(text)
        print("  tabular: OK")
    except Exception as e:
        print("  tabular:", type(e).__name__, e)
    try:
        kerned(text)
        print("  kerned: OK")
    except Exception as e:
        print("  kerned:", type(e).__name__, e)
