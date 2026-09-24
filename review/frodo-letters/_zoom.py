import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_p
from beadjoint.sheet import grid
from beadjoint.verify import check_glyph
P = full_p()
R = r"F:\code\beadjoint\review\frodo-letters"
caps = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
grid({c: P[c] for c in caps}, fr"{R}\z_caps.png", cols=9, scale=9, cell=(16, 24))
grid({c: P[c] for c in "abcdefghijklmnopqrstuvwxyz"}, fr"{R}\z_lower.png", cols=9, scale=9, cell=(16, 24))
grid({c: P[c] for c in "0O1Il|5S8B2Z6G9gqCcDd"}, fr"{R}\z_conf.png", cols=11, scale=9, cell=(14, 24))
spec = "ßæœÆŒðÐþÞøØłŁđħĦŧŦĸŋŊŀĿſĳĲıȷŉ"
grid({c: P[c] for c in spec}, fr"{R}\z_spec.png", cols=10, scale=9, cell=(16, 26))
for c in caps + spec:
    r = check_glyph(P[c].geom)
    print(c, r["thickness"], r["at"], "thin", r["thin"], "isl", r["islands"], [round(v, 2) for v in P[c].bounds])
