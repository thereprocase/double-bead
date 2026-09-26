"""Discover numeric construction parameters and export minimal, ordinary Git patches.

Only finite numbers replace numeric AST nodes in trusted repository sources. The
browser cannot provide Python, filenames, operators, or executable expressions.
Byte offsets are deliberate: Python AST columns count UTF-8 bytes, not characters.
"""
import ast
import difflib
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = ("beadjoint/glyphs.py", "beadjoint/latin.py", "beadjoint/marks.py", "beadjoint/geom.py")
FUNCTIONS = {
    "_raw_p": "Base", "_raw_m_rebuilt": "Mono", "_raw_one_tabular": "Footed 1",
    "capitals": "Capitals", "symbols": "Symbols", "specials": "Specials",
    "mono_narrow": "Mono", "square_w": "Shared w", "_pointed_m": "Shared M / W",
}
HELPERS = {"_raw_one_tabular": "1", "square_w": "w", "_pointed_m": "M"}
ACCENTS = {"grave": "à", "acute": "á", "circumflex": "â", "caron": "č", "breve": "ă",
           "tilde": "ã", "macron": "ā", "dot": "ż", "dieresis": "ä", "ring": "å",
           "doubleacute": "ő", "commaabove": "ģ", "commabelow": "ș"}


def number(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = number(node.operand)
        if v is not None:
            return -v if isinstance(node.op, ast.USub) else v
    return None


class Catalog:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.sources = {p: (self.root / p).read_bytes() for p in SOURCE_PATHS}
        self.hashes = {p: hashlib.sha256(s).hexdigest() for p, s in self.sources.items()}
        self.slots = {}
        self.targets = []
        for path, source in self.sources.items():
            tree = ast.parse(source, filename=path)
            for fn in tree.body:
                if isinstance(fn, ast.FunctionDef) and fn.name in FUNCTIONS:
                    if fn.name in HELPERS:
                        self._target(path, fn, HELPERS[fn.name], FUNCTIONS[fn.name], fn.body)
                    else:
                        for stmt in fn.body:
                            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                                continue
                            target = stmt.targets[0]
                            if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
                                char = target.slice.value
                                if not isinstance(char, str) or len(char) != 1:
                                    continue
                                if fn.name == "_raw_p" and char in "1w" or fn.name == "_raw_m_rebuilt" and char == "w":
                                    continue  # superseded by footed 1 and square_w in the actual font
                                self._target(path, stmt, char, FUNCTIONS[fn.name], [stmt.value])
                            elif fn.name == "symbols" and isinstance(target, ast.Name) and target.id in ("head", "tick"):
                                self._target(path, stmt, "’" if target.id == "head" else "'", "Shared punctuation", [stmt.value])
                if isinstance(fn, ast.Assign) and isinstance(fn.targets[0], ast.Name):
                    if fn.targets[0].id == "SHAPES":
                        for key, value in zip(fn.value.keys, fn.value.values):
                            self._target(path, value, ACCENTS[key.value], "Accent " + key.value, [value])
                    elif fn.targets[0].id == "DOT":
                        self._target(path, fn, ".", "Global dot radius", [fn.value], scalar=True)

    def _target(self, path, node, char, group, roots, scalar=False):
        ident = f"{path}:{node.lineno}:{node.col_offset}"
        target = {"id": ident, "char": char, "group": group, "path": path, "line": node.lineno,
                  "family": "M" if group == "Mono" else "P", "slots": [], "handles": []}
        source = self.sources[path]
        lines = source.splitlines(keepends=True)
        starts, offset = [], 0
        for line in lines:
            starts.append(offset)
            offset += len(line)

        def add(n, label, kind="coordinate"):
            value = number(n)
            if value is None:
                return None
            sid = f"{path}:{n.lineno}:{n.col_offset}"
            slot = {"id": sid, "label": label, "value": value, "kind": kind,
                    "path": path, "start": starts[n.lineno - 1] + n.col_offset,
                    "end": starts[n.end_lineno - 1] + n.end_col_offset}
            self.slots[sid] = slot
            if not any(s["id"] == sid for s in target["slots"]):
                target["slots"].append(slot)
            return sid

        calls = [n for root in roots for n in ast.walk(root) if isinstance(n, ast.Call)]
        direct = all(isinstance(n.func, ast.Name) and n.func.id in ("S", "So", "D", "Rect") for n in calls)
        for i, call in enumerate(calls):
            if not isinstance(call.func, ast.Name):
                continue
            name = call.func.id
            if name not in ("S", "So", "D", "Rect"):
                continue
            prefix = f"{name}{i + 1}"
            if name == "Rect":
                for n, label in zip(call.args, ("x₀", "y₀", "x₁", "y₁")):
                    add(n, prefix + " " + label)
                continue
            pts = call.args[:1] if name == "D" else call.args
            for j, pt in enumerate(pts):
                if not isinstance(pt, (ast.Tuple, ast.List)) or len(pt.elts) < 2:
                    continue
                x = add(pt.elts[0], f"{prefix} point {j + 1} x")
                y = add(pt.elts[1], f"{prefix} point {j + 1} y")
                if direct and x and y:
                    target["handles"].append({"x": x, "y": y, "label": f"{prefix}.{j + 1}"})
                if len(pt.elts) == 3:
                    add(pt.elts[2], f"{prefix} point {j + 1} corner radius", "radius")
            if name == "D" and len(call.args) > 1:
                add(call.args[1], prefix + " disk radius", "radius")
        if scalar:
            add(roots[0], "Dot radius (w)", "radius")
        if target["slots"]:
            # Shared helpers may include nested transforms: only show handles when
            # their coordinates are also the displayed glyph coordinates.
            if group in ("Mono", "Shared M / W") or group.startswith("Accent"):
                target["handles"] = []
            self.targets.append(target)

    def assert_fresh(self):
        for path, original in self.sources.items():
            if (self.root / path).read_bytes() != original:
                raise ValueError("Sources changed on disk. Restart the tuner before editing or exporting.")

    def validate(self, session):
        if not isinstance(session, dict) or session.get("schema") != 1:
            raise ValueError("Expected a version 1 tuner session.")
        if session.get("sources") != self.hashes:
            raise ValueError("Session belongs to different source files. Use its original checkout or rebase its patch.")
        values = session.get("values")
        if not isinstance(values, dict) or len(values) > len(self.slots):
            raise ValueError("Invalid parameter map.")
        clean = {}
        for sid, value in values.items():
            if sid not in self.slots:
                raise ValueError("Unknown source parameter.")
            if type(value) not in (int, float) or not math.isfinite(value) or not -32 <= value <= 32:
                raise ValueError("Coordinates must be finite numbers between -32 and 32w.")
            if self.slots[sid]["kind"] == "radius" and not 0 <= value <= 8:
                raise ValueError("Radii must be between 0 and 8w.")
            if value != self.slots[sid]["value"]:
                clean[sid] = value
        return clean

    def edited_sources(self, session):
        values = self.validate(session)
        out = {}
        for path, source in self.sources.items():
            edits = [(self.slots[sid], value) for sid, value in values.items() if self.slots[sid]["path"] == path]
            if not edits:
                continue
            for slot, value in sorted(edits, key=lambda e: e[0]["start"], reverse=True):
                literal = str(int(value)) if value == int(value) else repr(value)
                source = source[:slot["start"]] + literal.encode("ascii") + source[slot["end"]:]
            ast.parse(source, filename=path)
            out[path] = source
        return out

    def patch(self, session):
        self.assert_fresh()
        chunks = []
        for path, edited in self.edited_sources(session).items():
            chunks.append(f"diff --git a/{path} b/{path}\n")
            chunks.extend(difflib.unified_diff(self.sources[path].decode().splitlines(True), edited.decode().splitlines(True),
                                             fromfile="a/" + path, tofile="b/" + path))
        return "".join(chunks)
