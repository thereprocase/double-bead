import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_m
from beadjoint.setting import tabular

m = full_m()
print("W" in m, "M" in m, "V" in m)
try:
    tabular("WIDTH")
except Exception as e:
    print("ERROR:", e)
