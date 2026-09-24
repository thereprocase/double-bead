"""Build Double bead: fonts, specimen images and the verification report.

    cadpy build.py            -> fonts/*.ttf, specimen/*.png, report.json

Checks (spec 11), all of which must pass or the build exits 1:
  * every glyph of P, M and the tabular 1: thickness <= 2.85w, no thin pieces
  * every outline read back from each TTF lies within 1.5 font units (0.03w: vertex rounding
    0.014w, simplification 0.004w, centroid alignment) of its source glyph, and passes the same
    checks with the thin radius lowered by one unit (a 2w disk rounded to the spec's 50 units/w
    grid loses up to 0.014w of radius; the 40 px/w raster tolerates 0.002w on a disk)
  * set lines in all three settings, from the source geometry and from each TTF's own metrics
    and kern table: every neighbour pair >= 1.98w apart
  * each TTF reproduces its setting: every neighbour gap (word spaces included) within 0.13w of
    the setting engine (the spec's 0.1w kern drop plus rounding); cumulative drift reported
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from beadjoint.charset import full_m, full_mixed, full_p, glyph_name  # noqa: E402
from beadjoint.fontfile import KERN_DROP, UNITS, build_all  # noqa: E402
from beadjoint.glyphs import FIGURES, LOWER, set_m, set_mixed, set_p  # noqa: E402
from beadjoint.readback import FontReader  # noqa: E402
from beadjoint.setting import kerned, mixed, tabular  # noqa: E402
from beadjoint.specimen import draw_rows, thickness_map  # noqa: E402
from beadjoint.verify import LINE_MIN, THIN_R, check_glyph, check_set, line_gaps  # noqa: E402
from shapely import affinity  # noqa: E402

LINES = [LOWER, FIGURES, "double bead", "the quick brown fox jumps over the lazy dog",
         "pack my box with five dozen liquor jugs", "0.25 1/16 3/32 7/8 13/32",
         '1/4" Jt.', '1/2" - 5/8" dep.', '9/16" Jt.', '1-1/8" - 1-13/32" dep.', '7/8" Jt.', '1-3/4" - 2-3/16" dep.']
GAP_TOL = KERN_DROP + 0.03
GRID = 1 / UNITS
OUTLINE_TOL = 1.5 * GRID


def _summary(results):
    worst = max(results.items(), key=lambda kv: kv[1]["thickness"])
    return {"max_thickness": worst[1]["thickness"], "max_at": worst[0],
            "others_max": max((v["thickness"] for c, v in results.items() if c not in "ft"), default=0),
            "thin": {c: v["thin"] for c, v in results.items() if v["thin"]},
            "tight": {c: v["tight"] for c, v in results.items() if v["tight"]},
            "fail": [c for c, v in results.items() if not v["ok"]]}


def _line_min(line):
    gaps = line_gaps([(c, g) for c, g, _ in line])
    return min((d for *_, d in gaps), default=99.0)


def main():
    failures = []
    report = {"glyphs": {}, "fonts": {}, "lines": {}}

    sets = {"P": set_p(), "M": set_m(), "T:1": {"1": set_mixed()["1"]}}
    for name, glyphs in sets.items():
        s = _summary(check_set(glyphs))
        report["glyphs"][name] = s
        failures += [f"glyph {name}:{c}" for c in s["fail"]]

    fonts = HERE / "fonts"
    report["fonts"] = build_all(fonts)
    setters = {"Double bead": (kerned, "DoubleBead-Regular.ttf"), "Double bead Tab": (mixed, "DoubleBeadTab-Regular.ttf"),
               "Double bead Mono": (tabular, "DoubleBeadMono-Regular.ttf")}
    for family, (setter, fname) in setters.items():
        reader = FontReader(fonts / fname)
        # the fonts are built from the finished full sets (spec sets plus the review rounds' redesigns)
        source = full_m() if "Mono" in family else (full_mixed() if "Tab" in family else full_p())
        res, dev = {}, {}
        for c, g in source.items():
            out = reader.outline(glyph_name(c))
            res[c] = check_glyph(out, thin_r=THIN_R - GRID)
            a, b = out.centroid, g.geom.centroid
            dev[c] = out.boundary.hausdorff_distance(affinity.translate(g.geom, a.x - b.x, a.y - b.y).boundary)
        s = _summary(res)
        s["max_outline_deviation"] = round(max(dev.values()), 4)
        report["fonts"][family]["readback_glyphs"] = s
        failures += [f"{family} outline {c}" for c in s["fail"]]
        failures += [f"{family} outline {c} deviates {d:.3f}w" for c, d in dev.items() if d > OUTLINE_TOL]
        report["lines"][family] = {}
        for text in LINES:
            src = setter(text)
            ttf = reader.layout(text)
            gap = lambda ln: [b.bounds[0] - a.bounds[2] for (_, a, _), (_, b, _) in zip(ln, ln[1:])]
            gap_dev = max((abs(x - y) for x, y in zip(gap(src), gap(ttf))), default=0.0)
            drift = max(abs((gs.bounds[0] - src[0][1].bounds[0]) - (gt.bounds[0] - ttf[0][1].bounds[0]))
                        for (_, gs, _), (_, gt, _) in zip(src, ttf))
            entry = {"source_min_gap": round(_line_min(src), 3), "ttf_min_gap": round(_line_min(ttf), 3),
                     "ttf_gap_dev": round(gap_dev, 3), "ttf_drift": round(drift, 3),
                     "width": round(max(g.bounds[2] for _, g, _ in src) - min(g.bounds[0] for _, g, _ in src), 2)}
            report["lines"][family][text] = entry
            if entry["source_min_gap"] < LINE_MIN or entry["ttf_min_gap"] < LINE_MIN:
                failures.append(f"{family} line {text!r} gap")
            if gap_dev > GAP_TOL:
                failures.append(f"{family} line {text!r} gap deviation {gap_dev:.3f}")

    spec = HERE / "specimen"
    spec.mkdir(exist_ok=True)
    reader = FontReader(fonts / "DoubleBeadTab-Regular.ttf")
    draw_rows([("Double bead  (set P, kerned)", [kerned("double bead"), kerned(LOWER)]),
               ("Double bead Tab  (mixed setting: tabular figures, 1 on a 9w cell)", [mixed(FIGURES), mixed("0.25 1/16 3/32 7/8 13/32")]),
               ("Double bead Mono  (set M, 12w cells)", [tabular(LOWER[:13]), tabular(LOWER[13:]), tabular(FIGURES)]),
               ("Masonry key labels, set from DoubleBeadTab-Regular.ttf", [reader.layout('1/4" Jt.'), reader.layout('1/2" - 5/8" dep.'),
                                                                     reader.layout('1-1/8" - 1-13/32" dep.')])],
              scale=10, path=spec / "specimen.png")
    thickness_map([kerned(LOWER[:13]), kerned(LOWER[13:]), mixed(FIGURES), tabular(LOWER[:13]), tabular(LOWER[13:]),
                   mixed('1-1/8" - 1-13/32" dep.')], res=20, path=spec / "thickness.png")

    report["failures"] = failures
    (HERE / "report.json").write_text(json.dumps(report, indent=1, default=str))
    for name, s in report["glyphs"].items():
        print(f"glyphs {name:4s} max {s['max_thickness']} ({s['max_at']}), others <= {s['others_max']}, thin {s['thin'] or 'none'}")
    for family, f in report["fonts"].items():
        rb = f["readback_glyphs"]
        worst = min(report["lines"][family].values(), key=lambda e: e["ttf_min_gap"])
        dev = max(e["ttf_gap_dev"] for e in report["lines"][family].values())
        drift = max(e["ttf_drift"] for e in report["lines"][family].values())
        print(f"{family:15s} {f['glyphs']} glyphs, {f.get('class_pairs', 0)} class pairs + {f.get('exceptions', 0)} exceptions | outlines within "
              f"{rb['max_outline_deviation']}w, max {rb['max_thickness']}, thin {rb['thin'] or 'none'} | lines min gap "
              f"{worst['ttf_min_gap']}, gap dev <= {dev}, drift <= {drift}")
    print("FAIL:\n  " + "\n  ".join(failures) if failures else "all checks pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
