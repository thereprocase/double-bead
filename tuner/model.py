"""Discover numeric construction parameters and export minimal, ordinary Git patches.

Only finite numbers replace numeric AST nodes in trusted repository sources. The
browser cannot provide Python, filenames, operators, or executable expressions.
Byte offsets are deliberate: Python AST columns count UTF-8 bytes, not characters.
"""
import ast
import difflib
import hashlib
import importlib
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = ("beadjoint/glyphs.py", "beadjoint/latin.py", "beadjoint/marks.py", "beadjoint/geom.py")
# Everything a preview reads: the whole package (settings, checks and limits live outside the four
# editable files) and the tuner code the worker runs from disk. A change to any of them makes
# earlier results stale, so the server refuses to continue until it is restarted.
DEPENDENCIES = ("beadjoint/*.py", "tuner/__init__.py", "tuner/model.py", "tuner/worker.py")


class TunerError(ValueError):
    """A problem to show the person using the tuner, with a short code the interface can act on."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code

    def payload(self):
        return {"error": str(self), "code": self.code}


@dataclass(frozen=True)
class Construction:
    """How the tuner lists the glyphs one piece of source draws.

    family is the family whose preview shows them ("P" or "M"). handles: the raw coordinates are
    the finished glyph's own coordinates, so its points may be dragged. char names the one glyph a
    helper returns; None for a function that fills a dict (g["a"] = ...). args are the construction
    functions whose results charset passes to this one, in order. softened: the family receives
    these glyphs through glyphs.set_m, which applies soft() first. A construction that is missing
    or yields nothing to edit stops the tuner, so a rename in the sources cannot silently drop it.
    """
    group: str
    family: str = "P"
    handles: bool = True
    char: str | None = None
    args: tuple = ()
    softened: bool = False


FUNCTIONS = {
    "_raw_p": Construction("Base"),
    "_raw_m_rebuilt": Construction("Mono", "M", handles=False, softened=True),
    "_raw_one_tabular": Construction("Footed 1", char="1"),
    "capitals": Construction("Capitals"),
    "symbols": Construction("Symbols", args=("_raw_p",)),
    "specials": Construction("Specials", args=("_raw_p", "capitals", "symbols")),
    "mono_narrow": Construction("Mono", "M", handles=False),
    "square_w": Construction("Shared w", char="w"),
    "_pointed_m": Construction("Shared M / W", handles=False, char="M"),
    "extras": Construction("Specials"),
    "mono_extras": Construction("Mono", "M", handles=False),
}
# Pieces a construction function assigns to a local name and reuses in several glyphs.
SHARED = {
    ("symbols", "head"): Construction("Shared punctuation", char="’"),
    ("symbols", "tick"): Construction("Shared punctuation", char="'"),
    ("symbols", "frac_slash"): Construction("Shared fraction slash", handles=False, char="½"),
}
# marks.SHAPES entry -> a character that shows the mark in the preview.
ACCENTS = {"grave": "à", "acute": "á", "circumflex": "â", "caron": "č", "breve": "ă",
           "tilde": "ã", "macron": "ā", "dot": "ż", "dieresis": "ä", "ring": "å",
           "doubleacute": "ő", "commaabove": "ģ", "commabelow": "ș"}
# Calls whose numeric arguments are construction coordinates and radii.
CONSTRUCTORS = ("S", "So", "D", "Rect", "diagonal")
COMMIT = re.compile(r"[0-9a-f]{7,64}")


def number(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = number(node.operand)
        if v is not None:
            return -v if isinstance(node.op, ast.USub) else v
    return None


def dependencies(root):
    """{repo-relative path: bytes} of every file a preview reads (DEPENDENCIES) that exists under root."""
    root = Path(root)
    paths = sorted({f.relative_to(root).as_posix() for pattern in DEPENDENCIES for f in root.glob(pattern) if f.is_file()})
    return {path: (root / path).read_bytes() for path in paths}


def source_commit(root, paths):
    """HEAD when root is a Git checkout whose committed files match paths on disk, else None.

    A session is resumed by checking out its commit, so a commit that does not reproduce the
    files being edited (uncommitted or untracked changes, root inside another repository, no Git
    at all) would send people to the wrong place.
    """
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10)

    try:
        top = git("rev-parse", "--show-toplevel")
        if top.returncode or Path(top.stdout.strip()).resolve() != Path(root).resolve():
            return None
        head = git("rev-parse", "--verify", "-q", "HEAD")
        if head.returncode or git("ls-files", "--error-unmatch", "--", *paths).returncode:
            return None
        if git("diff", "--quiet", "HEAD", "--", *paths).returncode:
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    commit = head.stdout.strip()
    return commit if COMMIT.fullmatch(commit) else None


def _session_commit(session):
    commit = session.get("commit") if isinstance(session, dict) else None
    return commit[:12] if isinstance(commit, str) and COMMIT.fullmatch(commit) else None


def _resume(commit):
    return f"git switch --detach {commit}, then restart the tuner"


class Catalog:
    """Every catalogued construction of the glyph sources and the numeric slots it exposes.

    With families=True the raw glyphs of the families are built once, to drop constructions a
    family no longer uses and to list composite characters. The worker only substitutes values
    and passes families=False; the server validates every session against the full check first.
    """

    def __init__(self, root=ROOT, families=True):
        self.root = Path(root)
        self.sources = {p: (self.root / p).read_bytes() for p in SOURCE_PATHS}
        for path, source in self.sources.items():
            if b"\r\n" in source:
                raise TunerError(f"{path} has Windows (CRLF) line endings, so exported patches would not apply to "
                                 "the repository. With no uncommitted changes, check the sources out again: "
                                 "git rm -r --cached -q beadjoint && git reset --hard", "sources")
        self.hashes = {p: hashlib.sha256(s).hexdigest() for p, s in self.sources.items()}
        self.inputs = dependencies(self.root)
        self.inputs.update(self.sources)
        self.slots = {}
        self.targets = []
        self.superseded = []
        self.derived = None
        self._found = {}        # construction name -> source path
        self._produced = set()  # construction names that yielded at least one target
        self._origin = {}       # target id -> FUNCTIONS name, for whole-glyph constructions
        self._titles = {}       # target id -> how messages name it
        self._spans = []        # (path, first line, last line, target)
        self._owner = {}        # slot id -> target
        for path, source in self.sources.items():
            for node in ast.parse(source, filename=path).body:
                if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS:
                    self._function(path, node)
                elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                    if name == "SHAPES" and isinstance(node.value, ast.Dict):
                        self._found_at("SHAPES", path)
                        self._accents(path, node.value)
                    elif name == "DOT":
                        self._found_at("DOT", path)
                        self._target(path, node, ".", Construction("Global dot radius", handles=False), [node.value],
                                     key="DOT", title="The dot radius", scalar=True)
        self._check_found()
        if families:
            self._check_families()

    def _found_at(self, name, path):
        if name in self._found:
            raise TunerError(f"{name} is defined in both {self._found[name]} and {path}; tuner/model.py cannot tell "
                             "which one the fonts use.", "sources")
        self._found[name] = path

    def _function(self, path, fn):
        self._found_at(fn.name, path)
        construction = FUNCTIONS[fn.name]
        if construction.char:
            self._target(path, fn, construction.char, construction, fn.body, key=fn.name, origin=fn.name)
            return
        for stmt in fn.body:
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
                char = target.slice.value
                if isinstance(char, str) and len(char) == 1:
                    self._target(path, stmt, char, construction, [stmt.value], key=fn.name, origin=fn.name)
            elif isinstance(target, ast.Name) and (fn.name, target.id) in SHARED:
                key = (fn.name, target.id)
                self._found_at(key, path)
                self._target(path, stmt, SHARED[key].char, SHARED[key], [stmt.value], key=key)

    def _accents(self, path, shapes):
        for key, value in zip(shapes.keys, shapes.values):
            name = key.value if isinstance(key, ast.Constant) else None
            if name not in ACCENTS:
                raise TunerError(f"marks.SHAPES has a mark {name!r} that the tuner has no preview character for. "
                                 "Add it to ACCENTS in tuner/model.py.", "sources")
            self._found_at(("SHAPES", name), path)
            self._target(path, value, ACCENTS[name], Construction("Accent " + name, handles=False), [value],
                         key=("SHAPES", name), title=f"The {name} accent")

    def _check_found(self):
        """Refuse to start when a listed construction is missing or yields nothing to edit.

        A construction written without literal numbers (DOT = 3 / 2, S(*GRAVE)) is found but has no
        parameters, which would drop it from the tuner as surely as a rename.
        """
        wanted = [(name, f"{name}() ({c.group})") for name, c in FUNCTIONS.items()]
        wanted += [(key, f"{key[1]} in {key[0]}() ({c.group})") for key, c in SHARED.items()]
        wanted += [(("SHAPES", name), f"marks.SHAPES[{name!r}]") for name in ACCENTS]
        wanted += [("DOT", "DOT")]
        missing = [label for key, label in wanted if key not in self._found]
        if "SHAPES" not in self._found:
            missing.append("marks.SHAPES")
        if missing:
            raise TunerError("tuner/model.py lists constructions that are not in the sources: " + ", ".join(missing)
                             + ". Update FUNCTIONS, SHARED or ACCENTS in tuner/model.py to match.", "sources")
        empty = [label for key, label in wanted if key not in self._produced]
        if empty:
            raise TunerError("These constructions have no literal numbers the tuner can edit: " + ", ".join(empty)
                             + ". Write their coordinates as numbers, or update tuner/model.py.", "sources")

    def _check_families(self):
        """Drop constructions their family replaces, and list the composite characters.

        charset can replace a construction after it is built (P's 1 is the footed 1 and its w the
        square w), so each construction's raw output is compared with the raw glyph its family
        assembles. Editing a replaced construction would change nothing in the fonts.
        """
        charset, geom, marks = (importlib.import_module("beadjoint." + m) for m in ("charset", "geom", "marks"))
        raw = {"P": charset.raw_p(), "M": charset.raw_m()}
        outputs = {}

        def output(name):
            if name not in outputs:
                module = importlib.import_module(self._found[name][:-3].replace("/", "."))
                outputs[name] = getattr(module, name)(*(output(a) for a in FUNCTIONS[name].args))
            return outputs[name]

        def same(a, b):
            return a is not None and a.wkb == b.wkb

        dropped = set()
        for target in self.targets:
            name = self._origin.get(target["id"])
            if name is None:
                continue
            construction = FUNCTIONS[name]
            built = output(name) if construction.char else output(name).get(target["char"])
            used = raw[target["family"]].get(target["char"])
            if built is None or not (same(used, built) or construction.softened and same(used, geom.soft(built))):
                dropped.add(target["id"])
        self.superseded = [(t["group"], t["char"]) for t in self.targets if t["id"] in dropped]
        self.targets = [t for t in self.targets if t["id"] not in dropped]
        self._spans = [s for s in self._spans if s[3]["id"] not in dropped]
        for sid in [sid for sid, t in self._owner.items() if t["id"] in dropped]:
            del self.slots[sid], self._owner[sid]
        self.derived = {}
        for ch in charset.CHARS:
            parts = marks.decompose(ch) if ch not in raw["P"] else None
            if parts:
                base, names = parts
                self.derived[ch] = {"base": marks.mark_base(base, names), "marks": names}

    def _target(self, path, node, char, construction, roots, key, origin=None, title=None, scalar=False):
        ident = f"{path}:{node.lineno}:{node.col_offset}"
        target = {"id": ident, "char": char, "group": construction.group, "path": path, "line": node.lineno,
                  "family": construction.family, "slots": [], "handles": []}
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
            self._owner[sid] = target
            if not any(s["id"] == sid for s in target["slots"]):
                target["slots"].append(slot)
            return sid

        def handle(x, y, label):
            if direct and x and y:
                target["handles"].append({"x": x, "y": y, "label": label})

        calls = [n for root in roots for n in ast.walk(root) if isinstance(n, ast.Call)]
        direct = all(isinstance(n.func, ast.Name) and n.func.id in CONSTRUCTORS for n in calls)
        # Number constructors in reading order so "S1" is the first S( on the displayed line;
        # ast.walk is breadth-first and would label the last stroke of a | b | c first.
        constructors = sorted((n for n in calls if isinstance(n.func, ast.Name) and n.func.id in CONSTRUCTORS),
                              key=lambda n: (n.lineno, n.col_offset))
        for i, call in enumerate(constructors):
            name = call.func.id
            prefix = f"{name}{i + 1}"
            if name == "Rect":
                for n, label in zip(call.args, ("x₀", "y₀", "x₁", "y₁")):
                    add(n, prefix + " " + label)
                continue
            if name == "diagonal":
                # diagonal(x0, y0, x1, y1, clip=(top, bottom)): the centreline's ends are glyph
                # coordinates; the clip lines are y values of the flat cuts.
                ends = [add(n, prefix + " " + label) for n, label in zip(call.args, ("x₀", "y₀", "x₁", "y₁"))]
                ends += [None] * (4 - len(ends))
                handle(ends[0], ends[1], prefix + ".1")
                handle(ends[2], ends[3], prefix + ".2")
                clips = [k.value for k in call.keywords if k.arg == "clip"] + call.args[4:5]
                for clip in clips:
                    if isinstance(clip, (ast.Tuple, ast.List)):
                        for n, label in zip(clip.elts, ("clip y₀", "clip y₁")):
                            add(n, prefix + " " + label)
                continue
            pts = call.args[:1] if name == "D" else call.args
            for j, pt in enumerate(pts):
                if not isinstance(pt, (ast.Tuple, ast.List)) or len(pt.elts) < 2:
                    continue
                x = add(pt.elts[0], f"{prefix} point {j + 1} x")
                y = add(pt.elts[1], f"{prefix} point {j + 1} y")
                handle(x, y, f"{prefix}.{j + 1}")
                if len(pt.elts) == 3:
                    add(pt.elts[2], f"{prefix} point {j + 1} corner radius", "radius")
            if name == "D" and len(call.args) > 1:
                add(call.args[1], prefix + " disk radius", "radius")
        if scalar:
            add(roots[0], "Dot radius (w)", "radius")
        if target["slots"]:
            if not construction.handles:
                target["handles"] = []
            self.targets.append(target)
            self._produced.add(key)
            self._titles[ident] = title or f"{char} ({construction.group})"
            self._spans.append((path, node.lineno, node.end_lineno, target))
            if origin:
                self._origin[ident] = origin

    def title(self, target):
        """How a message names a construction at the start of a sentence: "n (Base)", "The breve accent"."""
        return self._titles[target["id"]]

    def target_at(self, path, line):
        """The innermost catalogued construction whose source spans path:line, or None."""
        spans = [(last - first, target) for p, first, last, target in self._spans if p == path and first <= line <= last]
        return min(spans, key=lambda s: s[0])[1] if spans else None

    def changed_inputs(self):
        """Paths of the files a preview reads that differ on disk from when the tuner started."""
        changed = []
        for path, original in self.inputs.items():
            try:
                current = (self.root / path).read_bytes()
            except OSError:
                current = None
            if current != original:
                changed.append(path)
        return changed

    def assert_fresh(self, session=None):
        changed = self.changed_inputs()
        if changed:
            message = (f"{', '.join(changed)} changed on disk since the tuner started, so earlier previews no longer "
                       "apply. Restart the tuner to load the current files.")
            commit = _session_commit(session)
            if commit:
                message += f" This session was saved at commit {commit}; to resume it, run: {_resume(commit)}."
            raise TunerError(message, "sources_changed")

    def validate(self, session):
        if not isinstance(session, dict) or session.get("schema") != 1:
            raise TunerError("Expected a version 1 tuner session.", "bad_session")
        if session.get("sources") != self.hashes:
            commit = _session_commit(session)
            message = "This session was saved for different glyph source files than this checkout has."
            if commit:
                message += f" It was saved at commit {commit} — run: {_resume(commit)}."
            else:
                message += (" It does not record a commit: open it in the checkout it was saved in, or apply its "
                            "exported patch there and rebase it.")
            raise TunerError(message, "stale_session")
        values = session.get("values")
        if not isinstance(values, dict) or len(values) > len(self.slots):
            raise TunerError("The session's parameter list is not valid.", "bad_session")
        clean = {}
        for sid, value in values.items():
            if sid not in self.slots:
                raise TunerError("The session changes a parameter this version of the tuner does not offer.",
                                 "bad_session")
            slot = self.slots[sid]
            owner = self._owner[sid]
            where = self.title(owner) if len(owner["slots"]) == 1 else f"{self.title(owner)} {slot['label']}"
            # Integers are compared exactly: math.isfinite would overflow on a 400-digit one.
            if type(value) not in (int, float) or type(value) is float and not math.isfinite(value):
                raise TunerError(f"{where}: values must be finite numbers.", "bad_session")
            # A few source values (a clip box at x = 40) sit outside the normal range; they stay valid.
            lo, hi = (0, 8) if slot["kind"] == "radius" else (-32, 32)
            lo, hi = min(lo, slot["value"]), max(hi, slot["value"])
            if not lo <= value <= hi:
                kind = "radii" if slot["kind"] == "radius" else "coordinates"
                raise TunerError(f"{where}: {kind} must be between {lo:g} and {hi:g}w.", "bad_session")
            if value != slot["value"]:
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
        self.assert_fresh(session)
        chunks = []
        for path, edited in self.edited_sources(session).items():
            chunks.append(f"diff --git a/{path} b/{path}\n")
            chunks.extend(difflib.unified_diff(self.sources[path].decode().splitlines(True), edited.decode().splitlines(True),
                                             fromfile="a/" + path, tofile="b/" + path))
        return "".join(chunks)
