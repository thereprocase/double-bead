"""Build the Brewster Technical browser site (static, served on the LAN by site/serve.py).

    cadpy site/build_site.py [--demo demo/check-owt0.json] [--crops demo/glyphs]

Writes site/dist: index.html, style.css, app.js (from site/template), data/glyphs.json,
data/summary.json, fonts/, crops/ (demo-slice bead renders), thick/ (local stroke width maps),
and the spec and README for download.
"""
import datetime
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(ROOT))
from beadjoint.charset import CHARS, full_m, full_p  # noqa: E402
from beadjoint.glyphs import pieces  # noqa: E402
from beadjoint.verify import check_glyph, opening, raster  # noqa: E402

arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
DIST = HERE / "dist"
from beadjoint.fontfile import VERSION
TH_RES = 16
TH_COLORS = [(0.0, (139, 150, 161)), (2.3, (226, 163, 59)), (2.86, (226, 91, 79))]


def path_d(geom):
    out = []
    for p in pieces(geom):
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)[:-1]
            out.append("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + "Z")
    return "".join(out)


def group(c):
    cat = unicodedata.category(c)
    if cat.startswith("L"):
        d = unicodedata.decomposition(c)
        return "accented" if d and not d.startswith("<") else "letters"
    if cat == "Nd" or c in "¹²³¼½¾":
        return "figures"
    if cat.startswith("P"):
        return "punct"
    return "symbols"


def thick_png(geom, path):
    mask = raster(geom, TH_RES, pad=1.0)
    img = np.zeros(mask.shape + (3,), np.uint8)
    img[:] = (27, 29, 32)
    for t, col in TH_COLORS:
        sel = mask if t == 0 else (opening(mask, t / 2 - 0.5 / TH_RES, TH_RES) & mask)
        img[sel] = col
    Image.fromarray(img).save(path)


def read_log():
    log = ROOT / "review" / "LOG.md"
    if not log.exists():
        return []
    rounds, cur = [], None
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "items": []}
            rounds.append(cur)
        elif line.startswith("- ") and cur:
            cur["items"].append(line[2:].strip())
    return rounds[::-1]


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    for sub in ("data", "fonts", "crops", "thick"):
        (DIST / sub).mkdir(parents=True)
    for f in ("index.html", "style.css", "app.js"):
        shutil.copy2(HERE / "template" / f, DIST / f)
    for f in (ROOT / "fonts").glob("*.ttf"):
        shutil.copy2(f, DIST / "fonts" / f.name)
    shutil.copy2(ROOT / "OFL.txt", DIST / "OFL.txt")
    shutil.copy2(ROOT / "OFL.txt", DIST / "fonts" / "OFL.txt")
    shutil.copy2(ROOT / "docs" / "SPEC.md", DIST / "SPEC.md")
    if (ROOT / "README.md").exists():
        shutil.copy2(ROOT / "README.md", DIST / "README.md")
    shutil.copy2(ROOT / "review" / "LOG.md", DIST / "LOG.md")
    demo_path = ROOT / arg("--demo", "demo/check-owt0.json")
    demo = json.loads(demo_path.read_text(encoding="utf-8"))["glyphs"] if demo_path.exists() else {}
    crops = ROOT / arg("--crops", "demo/glyphs")
    notes = {}
    notes_file = ROOT / "review" / "notes.json"
    if notes_file.exists():
        notes = json.loads(notes_file.read_text(encoding="utf-8"))
    P, M = full_p(), full_m()
    out, fails, over = [], [], 0
    for c in CHARS:
        g = P[c]
        r = check_glyph(g.geom)
        ps = pieces(g.geom)
        gap = min((a.distance(b) for i, a in enumerate(ps) for b in ps[i + 1:]), default=99.0)
        ok = r["ok"] and gap >= 1.98
        over += r["thickness"] > 2.85
        if not ok:
            fails.append(c)
        x0, _, x1, _ = g.geom.bounds
        cx, vw = (x0 + x1) / 2, max(16.0, x1 - x0 + 2)
        cp = f"{ord(c):04X}"
        thick_png(g.geom, DIST / "thick" / f"{cp}.png")
        for face in ("top", "bottom"):
            src = crops / f"{cp}-{face}.png"
            if src.exists():
                shutil.copy2(src, DIST / "crops" / src.name)
        d = demo.get(c, {})
        dsum = None
        if d:
            dsum = {"pass": bool(d["top"]["pass"] and d["bottom"]["pass"])}
            for face in ("top", "bottom"):
                dsum[face] = {k: d[face][k] for k in ("pass", "covered", "void", "bleed", "fat", "w_min", "w_max")}
        out.append({"c": c, "cp": cp, "name": unicodedata.name(c, f"U+{cp}").title(), "group": group(c),
                    "d": path_d(g.geom), "vb": [round(cx - vw / 2, 3), -12.5, round(vw, 3), 30.0],
                    "width": round(x1 - x0, 3), "mono": c in M,
                    "checks": {"ok": ok, "thickness": r["thickness"], "thin": r["thin"], "islands": r["islands"],
                               "piece_gap": round(gap, 3)},
                    "demo": dsum, "crops": {"top": f"crops/{cp}-top.png", "bottom": f"crops/{cp}-bottom.png"},
                    "thick": f"thick/{cp}.png", "note": notes.get(c)})
    faces = [f for g in out if g["demo"] for f in (g["demo"]["top"], g["demo"]["bottom"])]
    demo_fail = [g["c"] for g in out if g["demo"] and not g["demo"]["pass"]]
    summary = {
        "version": VERSION, "count": len(out), "built": datetime.date.today().isoformat(),
        "demo": {"pass": sum(1 for f in faces if f["pass"]), "total": len(faces)},
        "checks": [
            {"title": "Thin ink", "state": "ok" if not fails else "bad", "value": f"{len(out) - len(fails)} / {len(out)}",
             "text": "No part of any glyph is narrower than two line widths, no enclosed hole is narrower than two, and separate pieces sit at least two apart.",
             "items": [f"{c} U+{ord(c):04X}" for c in fails]},
            {"title": "Two beads or infill", "state": "ok", "value": f"{over} with infill",
             "text": "Strokes are two beads; crossings, filled pinches and joints wider than 2.85 w print with extra beads or infill, which is allowed."},
            {"title": "Demo slice", "state": "ok" if not demo_fail else "warn",
             "value": f"{summary_pass(faces)} / {len(faces)} faces",
             "text": "Every glyph sliced at native size on a coupon (Orca 2.4.2, Arachne, 0.3 nozzle as 0.4, 0.32 mm walls): colour covers at least 97 % of the glyph interior, no void over 0.03 mm² (half a bead square), colour bulge under 4 %, no stroke printed as one bead.",
             "items": [f"{c} U+{ord(c):04X}" for c in demo_fail][:40]},
        ],
        "log": read_log(),
        "files": [
            {"name": "OFL.txt", "href": "OFL.txt", "text": "SIL Open Font License 1.1 and Reserved Font Names"},
            {"name": "BrewsterTechnical-Regular.ttf", "href": "fonts/BrewsterTechnical-Regular.ttf", "text": "fully proportional, kerned: best for labels"},
            {"name": "BrewsterTechnicalTab-Regular.ttf", "href": "fonts/BrewsterTechnicalTab-Regular.ttf", "text": "proportional letters, tabular figures: numbers stacked in a column"},
            {"name": "BrewsterTechnicalMono-Regular.ttf", "href": "fonts/BrewsterTechnicalMono-Regular.ttf", "text": "monospace, 12 w cells"},
            {"name": "README.md", "href": "README.md", "text": "sizing table, rules, slicer profile, how to build"},
            {"name": "SPEC.md", "href": "SPEC.md", "text": "the two-bead font specification the design follows"},
            {"name": "LOG.md", "href": "LOG.md", "text": "the design log, one entry per review round"},
        ],
    }
    (DIST / "data" / "glyphs.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DIST / "data" / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"site: {len(out)} glyphs, design fails {len(fails)}, demo faces pass {summary['demo']['pass']}/{len(faces)} -> {DIST}")


def summary_pass(faces):
    return sum(1 for f in faces if f["pass"])


if __name__ == "__main__":
    main()
