"""Frodo r3 copy of demo/demo_plate.py: slices prototype glyphs from review/frodo-r3/<proto>.py (GLYPHS = [(label, geom)])
instead of the character set; labels are private-use characters so the checker keeps them apart.

    cadpy review/frodo-r3/plate.py --proto proto_cross --out review/frodo-r3/sl/<tag> --layout-out review/frodo-r3/sl/<tag>.layout.json [--set k=v]

Original doc: Demo slice: every Beadjoint glyph on one coupon, in colour on both faces, sliced with the
0.3-as-0.4 Arachne text profile of the masonry-keys project.

    cadpy demo/demo_plate.py [--w 0.32] [--out demo/slice] [--chars "zw#t"] [--layout-out demo/layout.json]
                             [--set key=value ...]     (process overrides, repeatable)

Coupon: 1.16 mm (0.2 + 6 x 0.16) with the text 0.36 mm deep on the top face (layers 6-7, reads from
above) and on the bed face (layers 1-2, mirrored so it reads from below). Glyphs in rows, 5w apart,
at their native size (em = 20 w). Writes demo/layout.json (every glyph's outline in coupon mm, both
faces) for demo_check.py.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import cadquery as cq
from shapely import affinity
from shapely.geometry import mapping

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "F:/code/masonry-keys")
import build_plate as bp  # noqa: E402  (3MF helpers: mesh, add_mesh, NS, ORCA)
from beadjoint.charset import CHARS, full_p  # noqa: E402
from beadjoint.glyphs import pieces  # noqa: E402

arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
W = float(arg("--w", "0.32"))
OUT = ROOT / arg("--out", "review/frodo-r3/sl/default")
PROFILES = Path("F:/code/masonry-keys/profiles-03as04-arachne")
THICK, DEPTH = 1.16, 0.36
GAP, PITCH, MARGIN, ROW_LEN = 5.0, 30.0, 4.0, 190.0     # w, w, mm, mm
TOP_Y = 13.0                                            # w below the row top where y = 0 (x-height line) sits


def layout():
    """Glyph outlines in coupon mm (y up), as read from above; rows fill left to right."""
    import importlib
    sys.path.insert(0, str(HERE))
    proto = importlib.import_module(arg("--proto", "proto_cross")).GLYPHS
    placed, x, row = [], 0.0, 0
    for c, g in proto:
        x0, _, x1, _ = g.bounds
        if (x + (x1 - x0)) * W > ROW_LEN:
            x, row = 0.0, row + 1
        gx = x - x0
        geom = affinity.affine_transform(g, [W, 0, 0, -W, gx * W, -(row * PITCH + TOP_Y) * W])
        placed.append((c, geom))
        x += (x1 - x0) + GAP
    minx = min(g.bounds[0] for _, g in placed); maxx = max(g.bounds[2] for _, g in placed)
    miny = min(g.bounds[1] for _, g in placed); maxy = max(g.bounds[3] for _, g in placed)
    dx, dy = MARGIN - minx, MARGIN - miny
    placed = [(c, affinity.translate(g, dx, dy)) for c, g in placed]
    size = (maxx - minx + 2 * MARGIN, maxy - miny + 2 * MARGIN)
    return placed, size


def solid(geoms, z0):
    solids = []
    for g in geoms:
        for p in pieces(g):
            outer = cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in p.exterior.coords[:-1]], close=True)
            inner = [cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in h.coords[:-1]], close=True) for h in p.interiors]
            solids.append(cq.Solid.extrudeLinear(cq.Face.makeFromWires(outer, inner), cq.Vector(0, 0, DEPTH)))
    return cq.Compound.makeCompound(solids)


def main():
    placed, (sx, sy) = layout()
    bottom = [(c, affinity.scale(g, -1, 1, origin=(sx / 2, 0))) for c, g in placed]
    (ROOT / arg("--layout-out", "review/frodo-r3/sl/default.layout.json")).write_text(json.dumps(
        {"w": W, "size_mm": [sx, sy], "thick": THICK, "depth": DEPTH,
         "glyphs": [{"char": c, "top": mapping(t), "bottom": mapping(b)} for (c, t), (_, b) in zip(placed, bottom)]},
        ensure_ascii=False), encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(dir=str(HERE)))
    try:
        cq.exporters.export(cq.Workplane().box(sx, sy, THICK, centered=False), str(tmp / "body.stl"))
        cq.exporters.export(cq.Workplane().newObject([solid([g for _, g in placed], THICK - DEPTH)]), str(tmp / "top.stl"),
                            tolerance=0.004, angularTolerance=0.05)
        cq.exporters.export(cq.Workplane().newObject([solid([g for _, g in bottom], 0.0)]), str(tmp / "bottom.stl"),
                            tolerance=0.004, angularTolerance=0.05)
        parts = {p: bp.mesh(tmp / f"{p}.stl") for p in ("body", "top", "bottom")}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    NS = bp.NS
    root = ET.Element(f"{{{NS}}}model", {"unit": "millimeter", "xml:lang": "en-US"})
    res = ET.SubElement(root, f"{{{NS}}}resources")
    build = ET.SubElement(root, f"{{{NS}}}build")
    ids = {}
    for i, (p, (vs, fs, _, _)) in enumerate(parts.items(), 1):
        ids[p] = i
        bp.add_mesh(res, i, p, vs, fs)
    po = ET.SubElement(res, f"{{{NS}}}object", {"id": "4", "type": "model", "name": "Beadjoint demo"})
    cs = ET.SubElement(po, f"{{{NS}}}components")
    for p in ("body", "top", "bottom"):
        ET.SubElement(cs, f"{{{NS}}}component", {"objectid": str(ids[p])})
    ox, oy = (256 - sx) / 2, (256 - sy) / 2
    ET.SubElement(build, f"{{{NS}}}item", {"objectid": "4", "transform": f"1 0 0 0 1 0 0 0 1 {ox:.4f} {oy:.4f} 0"})
    settings = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>", '  <object id="4">',
                '    <metadata key="name" value="Beadjoint demo"/>', '    <metadata key="extruder" value="1"/>']
    for p, sub, ext in (("body", "normal_part", 1), ("top", "modifier_part", 2), ("bottom", "modifier_part", 2)):
        settings += [f'    <part id="{ids[p]}" subtype="{sub}">', f'      <metadata key="name" value="{p}"/>',
                     f'      <metadata key="extruder" value="{ext}"/>', "    </part>"]
    settings += ["  </object>", "</config>"]
    with zipfile.ZipFile(OUT / "input.3mf", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", ET.tostring(root, encoding="utf-8", xml_declaration=True))
        z.writestr("Metadata/model_settings.config", "\n".join(settings) + "\n")
    machine = json.loads((PROFILES / "machine.json").read_text(encoding="utf-8"))
    process = json.loads((PROFILES / "process.json").read_text(encoding="utf-8"))
    filament = json.loads((PROFILES / "filament.json").read_text(encoding="utf-8"))
    process.update({"enable_prime_tower": "0", "flush_volumes_matrix": ["0", "350", "250", "0"],
                    "flush_volumes_vector": ["140"] * 4, "flush_multiplier": ["1"]})
    for kv in [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--set"]:   # --set key=value
        k, v = kv.split("=", 1)
        process[k] = v
        print("override", k, "=", v)
    for name, data in (("machine.json", machine), ("process.json", process),
                       ("filament.json", dict(filament, filament_colour=["#1A1A1A"])),
                       ("filament2.json", dict(filament, filament_colour=["#F2C200"]))):
        (OUT / name).write_text(json.dumps(data, indent=1), encoding="utf-8")
    cmd = [bp.ORCA, "--datadir", str(OUT / "data"),
           "--load-settings", str(OUT / "machine.json") + ";" + str(OUT / "process.json"),
           "--load-filaments", str(OUT / "filament.json") + ";" + str(OUT / "filament2.json"),
           "--arrange", "0", "--orient", "0", "--slice", "0", "--export-3mf", "sliced.3mf",
           "--outputdir", str(OUT), str(OUT / "input.3mf")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print("coupon", round(sx, 1), "x", round(sy, 1), "mm,", len(placed), "glyphs; orca exit", r.returncode)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:])
        sys.exit(r.returncode)
    with zipfile.ZipFile(OUT / "sliced.3mf") as z:
        (OUT / "plate_1.gcode").write_bytes(z.read("Metadata/plate_1.gcode"))
    (OUT / "placement.json").write_text(json.dumps({"origin_mm": [ox, oy]}))


if __name__ == "__main__":
    main()
