import sys
from pathlib import Path; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_m, full_p, CHARS

m = full_m()
p = full_p()
missing = sorted(set(CHARS) - set(m.keys()))
print(f"{len(missing)} glyphs excluded from full_m():")
for c in missing:
    g = p[c]
    w = g.width
    cat = __import__("unicodedata").category(c)
    print(f"  {c!r:>6}  U+{ord(c):04X}  width={w:.2f}w  cat={cat}")
