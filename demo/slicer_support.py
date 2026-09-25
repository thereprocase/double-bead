"""Slicer plumbing for the demo coupon: 3MF mesh writing, OrcaSlicer lookup, gcode move parsing.

Everything the demo and review slicing scripts need beyond the beadjoint package and pinned
requirements lives here, so a fresh clone can slice and score a coupon on its own.

    NS                       3MF core namespace used for model XML elements
    ORCA                     OrcaSlicer executable ($ORCA_SLICER, else the first known name on PATH)
    PROFILES                 slicer profile directory ($FILLAPRINT_PROFILES, else demo/profiles)
    mesh(stl_path)           -> (vertices, triangles, min_xyz, max_xyz), vertices de-duplicated
    add_mesh(resources, id, name, vertices, triangles)   append a 3MF <object> with that mesh
    move_pieces(line, x, y)  -> (segments, new_x, new_y, e) for one G0/G1/G2/G3 line
"""
import math
import os
import shutil
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", NS)

HERE = Path(__file__).resolve().parent

_ORCA_NAMES = ("orca-slicer", "OrcaSlicer", "orcaslicer", "OrcaSlicer.exe", "orca-slicer.exe")


def _find_orca():
    env = os.environ.get("ORCA_SLICER")
    if env:
        return env
    for name in _ORCA_NAMES:
        found = shutil.which(name)
        if found:
            return found
    # Resolved lazily by subprocess; the error names the variable to set.
    return "orca-slicer"


ORCA = _find_orca()
PROFILES = Path(os.environ.get("FILLAPRINT_PROFILES", HERE / "profiles"))


def require_profiles(directory=None):
    """The profile directory, or exit with instructions if its three JSON files are missing."""
    d = Path(directory or PROFILES)
    missing = [n for n in ("machine.json", "process.json", "filament.json") if not (d / n).is_file()]
    if missing:
        raise SystemExit(f"slicer profiles missing in {d}: {', '.join(missing)}\n"
                         "Export them from OrcaSlicer as described in demo/profiles/README.md, "
                         "or point FILLAPRINT_PROFILES at a directory that has them.")
    return d


# --- 3MF -------------------------------------------------------------------------------------------

def _stl_triangles(path):
    """Triangles from an ASCII or binary STL, as lists of three (x, y, z) tuples."""
    data = Path(path).read_bytes()
    if len(data) >= 84:
        (count,) = struct.unpack_from("<I", data, 80)
        # A binary STL is exactly header + count + 50 bytes per facet; ASCII files rarely match that.
        if 84 + 50 * count == len(data):
            tris = []
            for i in range(count):
                v = struct.unpack_from("<12f", data, 84 + 50 * i)
                tris.append([v[3:6], v[6:9], v[9:12]])
            return tris
    tris, cur = [], []
    for line in data.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if parts and parts[0] == "vertex":
            cur.append(tuple(float(p) for p in parts[1:4]))
            if len(cur) == 3:
                tris.append(cur)
                cur = []
    return tris


def mesh(path):
    """Indexed mesh from an STL: (vertices, triangles, min_xyz, max_xyz).

    Vertices are merged on exact coordinates, which is what CadQuery's tessellation produces for
    shared edges; 3MF requires an indexed, manifold mesh rather than a triangle soup."""
    index, verts, faces = {}, [], []
    for tri in _stl_triangles(path):
        ids = []
        for v in tri:
            if v not in index:
                index[v] = len(verts)
                verts.append(v)
            ids.append(index[v])
        if len(set(ids)) == 3:          # drop degenerate facets
            faces.append(tuple(ids))
    if not verts:
        raise ValueError(f"no triangles in {path}")
    lo = tuple(min(v[i] for v in verts) for i in range(3))
    hi = tuple(max(v[i] for v in verts) for i in range(3))
    return verts, faces, lo, hi


def add_mesh(resources, obj_id, name, verts, faces):
    """Append a 3MF mesh object to a <resources> element and return it."""
    obj = ET.SubElement(resources, f"{{{NS}}}object", {"id": str(obj_id), "type": "model", "name": name})
    m = ET.SubElement(obj, f"{{{NS}}}mesh")
    vs = ET.SubElement(m, f"{{{NS}}}vertices")
    for x, y, z in verts:
        ET.SubElement(vs, f"{{{NS}}}vertex", {"x": f"{x:.6f}", "y": f"{y:.6f}", "z": f"{z:.6f}"})
    ts = ET.SubElement(m, f"{{{NS}}}triangles")
    for a, b, c in faces:
        ET.SubElement(ts, f"{{{NS}}}triangle", {"v1": str(a), "v2": str(b), "v3": str(c)})
    return obj


# --- gcode -----------------------------------------------------------------------------------------

ARC_SEG = 0.05   # mm; longest chord used to flatten G2/G3 arcs, well under the 0.01 mm raster's reach


def _words(line):
    code = line.split(";", 1)[0].split()
    return {w[0].upper(): float(w[1:]) for w in code[1:] if len(w) > 1 and w[0].isalpha()}


def move_pieces(line, x, y):
    """Straight segments swept by one move, assuming absolute XY and relative E (Orca's default).

    Returns (segments, new_x, new_y, e) where segments are (ax, ay, bx, by) tuples and e is the
    extrusion amount on this line (0 for travel). G2/G3 arcs use I/J centre offsets and are flattened
    into chords no longer than ARC_SEG."""
    cmd = line.split(None, 1)[0].upper()
    w = _words(line)
    nx, ny, e = w.get("X", x), w.get("Y", y), w.get("E", 0.0)
    if cmd in ("G0", "G1"):
        segs = [(x, y, nx, ny)] if (nx, ny) != (x, y) else []
        return segs, nx, ny, e
    if cmd not in ("G2", "G3"):
        return [], x, y, 0.0
    cx, cy = x + w.get("I", 0.0), y + w.get("J", 0.0)
    r = math.hypot(x - cx, y - cy)
    a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
    sweep = a1 - a0
    if cmd == "G2":                      # clockwise: negative sweep
        if sweep >= 0:
            sweep -= 2 * math.pi
    elif sweep <= 0:                     # G3 counter-clockwise: positive sweep
        sweep += 2 * math.pi
    n = max(1, math.ceil(abs(sweep) * r / ARC_SEG))
    pts = [(cx + r * math.cos(a0 + sweep * k / n), cy + r * math.sin(a0 + sweep * k / n)) for k in range(n)]
    pts.append((nx, ny))
    pts[0] = (x, y)
    segs = [(ax, ay, bx, by) for (ax, ay), (bx, by) in zip(pts, pts[1:])]
    return segs, nx, ny, e
