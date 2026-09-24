"""Score tuning runs: void area, glyph-faces over the void limit, coverage, single-bead runs."""
import json, sys
from pathlib import Path
rows = []
for f in sorted(Path("/mnt/f/code/beadjoint/demo").glob("check-tune-*.json")):
    r = json.loads(f.read_text(encoding="utf-8"))
    faces = [g[k] for g in r["glyphs"].values() for k in ("top", "bottom")]
    layers = [L for fc in faces for L in fc["layers"]]
    rows.append((sum(L["void"] for L in layers), f.stem[11:], sum(1 for fc in faces if fc["void"] > 0.02),
                 min(fc["covered"] for fc in faces), sum(fc["fat"] for fc in faces), max(fc["w_max"] or 0 for fc in faces)))
for v, tag, n, cov, single, wmax in sorted(rows):
    print(f"{tag:14s} void total {v:6.3f} mm2 | faces over 0.02: {n:2d} | min covered {cov:5.1f}% | single-bead {single:5.2f} mm | max bead {wmax:.2f}")
