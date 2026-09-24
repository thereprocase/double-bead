import sys, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_mixed
from beadjoint.setting import off
G = full_mixed()
chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
t0 = time.time()
hits = []
for a in chars:
    for b in chars:
        ga, gb = G[a], G[b]
        ov = ga.maxx - (off(ga, gb) + gb.minx)
        if ov > 1.0 + 1e-6:
            hits.append(f"{a}{b}:{ov:.1f}")
print(len(hits), "letter/figure pairs overlap > 1.0w:", " ".join(hits))
print("secs", round(time.time() - t0))
