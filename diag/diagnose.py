"""Temporary CI diagnostic: where do finished glyphs differ between platforms?

Writes one JSON file with library versions, a libm sample, a digest of every fillet() result, the
WKB digest of every glyph before and after finishing, a stage-by-stage trace of finishing for
suspect glyphs, and the read-back deviation of the committed fonts.
"""
import argparse
import hashlib
import json
import math
import platform
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy  # noqa: E402
import scipy  # noqa: E402
import shapely  # noqa: E402
import fontTools  # noqa: E402
from shapely import affinity  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from beadjoint import geom as G  # noqa: E402

SUSPECTS = [("M", "6"), ("M", "ż"), ("P", "Ů"), ("P", "Å"), ("M", "Ļ"), ("M", "z"), ("P", "U")]


def wkb(g):
    return shapely.to_wkb(g, byte_order=1, output_dimension=2, include_srid=False)


def h(g):
    return hashlib.sha256(wkb(g)).hexdigest()[:16]


def fh(x):
    return float(x).hex()


def parts(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]


# --- fillet digests: patch before any glyph is built --------------------------------------------
FILLETS = []
_real_fillet = G.fillet


def _fillet(a, p, b, r):
    pts, t = _real_fillet(a, p, b, r)
    buf = b"".join(struct.pack("<dd", x, y) for x, y in pts) + struct.pack("<d", t)
    FILLETS.append(hashlib.sha256(buf).hexdigest()[:12])
    return pts, t


G.fillet = _fillet

ROBUST = []
_real_robust = G._robust


def _robust(op):
    from shapely.errors import GEOSException
    try:
        return op()
    except GEOSException as exc:
        ROBUST.append(str(exc)[:200])
        return op(grid_size=1e-6)


G._robust = _robust


def libm_sample():
    xs = [k * 0.0137 + 0.001 for k in range(4000)]
    out = {}
    for name, f in (("sin", math.sin), ("cos", math.cos), ("tan", math.tan)):
        out[name] = [fh(f(x)) for x in xs]
    out["acos"] = [fh(math.acos((k % 2000) / 1000.0 - 0.9995)) for k in range(4000)]
    out["atan2"] = [fh(math.atan2(math.sin(x) * 3.1, x - 20.0)) for x in xs]
    return out


def geos_micro():
    cases = {
        "disk64": Point(0.1, 0.2).buffer(1.0, quad_segs=64),
        "disk64_r3": Point(2.0, -9.0).buffer(3.0, quad_segs=64),
        "line_mitre": LineString([(0, 0), (3.3, 1.7), (5.1, -2.2)]).buffer(1.0, cap_style="flat", join_style="mitre", mitre_limit=5.0),
        "soft_square": Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]).buffer(-0.5, quad_segs=64).buffer(0.5, quad_segs=64),
    }
    cases["union"] = cases["disk64"].union(cases["line_mitre"])
    cases["diff"] = cases["line_mitre"].difference(cases["disk64"])
    return {k: h(v) for k, v in cases.items()}


def trace_finish(g):
    """geom.finish step by step, recording every intermediate digest and every threshold decision."""
    t = {}
    # fill_pinches
    g0 = G._clean(g)
    t["fp.clean"] = h(g0)
    closed = G._clean(g0.buffer(G.PINCH_R, quad_segs=G.QS).buffer(-G.PINCH_R, quad_segs=G.QS))
    t["fp.closed"] = h(closed)
    extra = G._robust(lambda **k: closed.difference(g0, **k))
    t["fp.extra"] = h(extra)
    t["fp.extra_areas"] = sorted(round(p.area, 9) for p in parts(extra) if not p.is_empty)
    core = extra.buffer(-0.03)
    t["fp.core"] = h(core)
    polys = parts(core)
    t["fp.core_areas"] = sorted(round(q.area, 9) for q in polys if not q.is_empty)
    keep = [q for q in polys if not q.is_empty and q.area > G.PINCH_MIN_AREA]
    t["fp.keep"] = len(keep)
    if keep:
        fills = G._robust(lambda **k: unary_union(keep).buffer(0.06, quad_segs=G.QS).intersection(extra, **k))
        t["fp.fills"] = h(fills)
        out = G._robust(lambda **k: g0.union(unary_union([fills]), **k))
        t["fp.union"] = h(out)
        a = out.buffer(1e-3, join_style="mitre")
        t["fp.seal_out"] = h(a)
        fp = a.buffer(-1e-3, join_style="mitre")
    else:
        fp = g0
    t["fp"] = h(fp)
    ref = G.fill_pinches(g)
    t["fp.matches_geom"] = h(ref) == t["fp"]
    # fillet_inside
    r = 0.5
    g1 = G._clean(fp)
    t["fi.clean"] = h(g1)
    closed = G._clean(g1.buffer(r, quad_segs=G.QS).buffer(-r, quad_segs=G.QS))
    t["fi.closed"] = h(closed)
    extra = G._robust(lambda **k: closed.difference(g1, **k))
    t["fi.extra"] = h(extra)
    gb = g1.buffer(1e-3)
    t["fi.gb"] = h(gb)
    pieces = []
    keep = []
    for p in parts(extra):
        if p.is_empty or p.area < 1e-6:
            continue
        mouth = p.boundary.difference(gb).length
        kept = not (p.area <= G.FILLET_MIN_AREA and mouth > 1.2 * p.area ** 0.5)
        pieces.append([round(p.area, 9), round(mouth, 9), round(1.2 * p.area ** 0.5, 9), kept,
                       [round(v, 6) for v in p.bounds]])
        if kept:
            keep.append(p)
    t["fi.pieces"] = sorted(pieces)
    if keep:
        out = G._robust(lambda **k: g1.union(unary_union(keep), **k))
        t["fi.union"] = h(out)
        fi = out.buffer(1e-3, join_style="mitre").buffer(-1e-3, join_style="mitre")
    else:
        fi = g1
    t["fi"] = h(fi)
    # soft
    e = fi.buffer(-0.5, quad_segs=G.QS)
    t["soft.erode"] = h(e)
    s = e.buffer(0.5, quad_segs=G.QS)
    t["soft"] = h(s)
    t["finish.matches_geom"] = h(G.finish(g)) == t["soft"]
    t["bounds"] = [fh(v) for v in s.bounds]
    t["nverts"] = int(shapely.get_num_coordinates(s))
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--reference")
    args = ap.parse_args()
    t0 = time.time()
    res = {"env": {
        "python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
        "shapely": shapely.__version__, "geos": shapely.geos_version_string,
        "geos_capi": shapely.geos_capi_version_string, "numpy": numpy.__version__, "scipy": scipy.__version__,
        "fonttools": fontTools.version, "float_repr_style": sys.float_repr_style,
    }}
    print(json.dumps(res["env"], indent=1), flush=True)
    res["libm"] = libm_sample()
    res["geos_micro"] = geos_micro()

    from beadjoint import charset
    from beadjoint.charset import full_m, full_mixed, full_p, finish_inputs, glyph_name, raw_m, raw_p
    timings = {}
    t = time.time()
    rp = raw_p()
    rm = raw_m()
    timings["raw"] = time.time() - t
    res["raw"] = {"P": {c: h(g) for c, g in rp.items()}, "M": {c: h(g) for c, g in rm.items()}}
    t = time.time()
    fams = {"P": full_p(), "T": full_mixed(), "M": full_m()}
    timings["finish"] = time.time() - t
    inputs = finish_inputs()
    res["fillet"] = {"count": len(FILLETS), "digest": hashlib.sha256("".join(FILLETS).encode()).hexdigest(),
                     "calls": FILLETS}
    res["robust_fallbacks"] = list(ROBUST)
    res["families"] = {name: {c: [h(inputs[name][c]), h(g.geom), [fh(v) for v in g.bounds]]
                              for c, g in glyphs.items()} for name, glyphs in fams.items()}

    ref = json.loads(Path(args.reference).read_text(encoding="utf-8")) if args.reference else None
    suspects = list(SUSPECTS)
    diff = {}
    if ref:
        for name in ("P", "T", "M"):
            mine, theirs = res["families"][name], ref["families"][name]
            d_in = [c for c in mine if c in theirs and mine[c][0] != theirs[c][0]]
            d_out = [c for c in mine if c in theirs and mine[c][1] != theirs[c][1]]
            missing = sorted(set(theirs) ^ set(mine))
            diff[name] = {"input_differs": d_in, "output_differs": d_out, "set_difference": missing,
                          "output_differs_input_same": [c for c in d_out if c not in d_in]}
            for c in d_out:
                if name != "T" and (name, c) not in suspects:
                    suspects.append((name, c))
        diff["raw"] = {name: [c for c, v in res["raw"][name].items() if ref["raw"][name].get(c) != v] for name in ("P", "M")}
        diff["fillet_calls_differ"] = sum(1 for a, b in zip(res["fillet"]["calls"], ref["fillet"]["calls"]) if a != b)
        diff["fillet_count"] = [res["fillet"]["count"], ref["fillet"]["count"]]
        diff["libm_differs"] = {k: sum(1 for a, b in zip(v, ref["libm"][k]) if a != b) for k, v in res["libm"].items()}
        diff["geos_micro_differs"] = [k for k, v in res["geos_micro"].items() if ref["geos_micro"].get(k) != v]
        res["diff"] = diff
        print(json.dumps({k: (v if not isinstance(v, dict) else {kk: (vv[:60] if isinstance(vv, list) else vv)
                                                                   for kk, vv in v.items()}) for k, v in diff.items()},
                         ensure_ascii=False, indent=1), flush=True)

    trace = {}
    wkbs = {}
    for name, c in suspects[:60]:
        glyphs = fams[name]
        if c not in glyphs:
            continue
        trace[f"{name}:{c}"] = trace_finish(inputs[name][c])
        wkbs[f"{name}:{c}"] = {"in": wkb(inputs[name][c]).hex(), "out": wkb(glyphs[c].geom).hex()}
    res["trace"] = trace
    res["wkb"] = wkbs

    from beadjoint.readback import FontReader
    t = time.time()
    rb = {}
    files = {"P": "Fillaprint-Regular.ttf", "T": "FillaprintTab-Regular.ttf", "M": "FillaprintMono-Regular.ttf"}
    for name, fname in files.items():
        reader = FontReader(ROOT / "fonts" / fname)
        dev = {}
        for c, g in fams[name].items():
            out = reader.outline(glyph_name(c))
            a, b = out.centroid, g.geom.centroid
            dev[c] = out.boundary.hausdorff_distance(affinity.translate(g.geom, a.x - b.x, a.y - b.y).boundary)
        rb[name] = {c: round(d, 5) for c, d in sorted(dev.items(), key=lambda kv: -kv[1]) if d > 0.01}
    timings["readback"] = time.time() - t
    res["readback"] = rb
    band = {}
    for name, glyphs in fams.items():
        band[name] = sorted(c for c, g in glyphs.items() if g.bounds[1] < -12.0 - 1e-6 or g.bounds[3] > 14.0 + 1e-6)
    res["ink_band_outside"] = band
    timings["total"] = time.time() - t0
    res["timings"] = timings
    print(json.dumps({"readback_top": {k: dict(list(v.items())[:12]) for k, v in rb.items()},
                      "readback_over_0.03": {k: {c: d for c, d in v.items() if d > 0.03} for k, v in rb.items()},
                      "ink_band_outside": band, "robust_fallbacks": len(ROBUST), "timings": timings},
                     ensure_ascii=False, indent=1), flush=True)
    for key, tr in trace.items():
        print(key, json.dumps({k: v for k, v in tr.items() if not k.endswith("areas") and k != "fi.pieces"}, ensure_ascii=False))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
