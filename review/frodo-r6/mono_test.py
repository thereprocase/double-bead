import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.setting import tabular
from beadjoint.specimen import draw_rows

samples = [
    ("0/O 1/l/I distinction", "SN 0O1Il-8B5S"),
    ("thread callout", "M3x0.5"),
    ("code line", 'if (a[i] == 0) { x++; }'),
    ("windows path", r"C:\temp\file_01.txt"),
    ("aligned numbers 1", "  1234.56"),
    ("aligned numbers 2", "   -12.30"),
    ("aligned numbers 3", " 100.00 "),
    ("alphabet upper", "ABCDEFGHIJKLM"),
    ("alphabet upper 2", "NOPQRSTUVWXYZ"),
    ("alphabet lower", "abcdefghijklm"),
    ("alphabet lower 2", "nopqrstuvwxyz"),
    ("digits", "0123456789"),
]

rows = []
for cap, text in samples:
    try:
        line = tabular(text)
    except Exception as e:
        print(f"FAILED {cap!r} text={text!r}: {e}")
        continue
    rows.append((f"{cap}: {text}", [line]))

draw_rows(rows, scale=10, path=r"F:\code\beadjoint\review\frodo-r6\mono_samples.png")
print("done")
