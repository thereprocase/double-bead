# Local glyph tuner

The tuner edits numeric parameters in the **existing Python source**. It uses the
same constructors, finishing filters, accent composition, spacing engine, and
geometry checks as the font build. It exports ordinary Git patches, with no
second glyph format to maintain.

## Start

From a clone of this repository, using Python 3.12 or newer:

```sh
python -m venv .venv
# macOS / Linux:
. .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install --only-binary=:all: -r requirements.txt
python -m tuner.serve
```

Open **http://127.0.0.1:8766** if the browser does not open automatically. Use
`--port 8767` to choose another port or `--no-browser` to suppress opening a tab.
The server binds only to the local loopback interface. There are no accounts,
remote services, JavaScript packages, or additional Python dependencies. Bundled
IBM Plex fonts keep the Gridline interface available offline.

## Tune

1. Select a construction in the left rail. The initial catalog exposes **185
   constructions and 1,938 numeric parameters**, including base letters,
   capitals, symbols, Mono variants, accents, and the shared dot radius.
2. Drag yellow construction points where the finished glyph uses those same
   coordinates, or edit exact numbers in the right rail. Coordinates use `w`
   units and Y points down. A normal stroke stays **2w** wide.
3. Inspect the original and edited outlines, a sample word or phrase, and the
   geometry readouts. The line-width field only converts dimensions to mm.
4. Change the preview glyph to a derived character (for example `ñ` while
   editing the base `n`) or switch family. Base edits propagate through the
   real constructors; independent Mono replacements remain independent.
5. Run **Validate changed glyphs**. This compares all three families with the
   unmodified source and checks changed outlines, including derived accents.
6. Export a Git patch. Save a session JSON to share or resume the parameter
choices. Undo, redo, and reset are available; the browser also autosaves.

Session files contain repo-relative parameter identifiers, source hashes, and
numeric edits. They do not include the preview phrase, local filesystem paths,
usernames, machine details, or Git credentials. Nothing is uploaded by the tuner.

The server never edits your source files. Sessions contain source SHA-256 hashes
and are rejected when opened against different source files. If you edit Python
in another editor, restart the tuner. Applying a patch to a newer checkout is a
normal Git review/rebase operation; the tuner does not guess at changed offsets.

Construction points can coincide. Moving one does not automatically move the
other; use the numeric fields to edit both. Transformed shapes and accent marks
use numeric controls, because their raw points do not sit in the final glyph's
coordinate system. Initial previews can take several seconds; the server runs
each computation in an isolated process and caches recent results. Stale or
failed previews are dimmed and labeled.

## Contribute

```sh
git switch -c glyph/my-adjustment
git apply --check /path/to/fillaprint-glyphs.patch
git apply /path/to/fillaprint-glyphs.patch
python build.py
python -m unittest discover -s tests
git diff -- beadjoint/
```

Open a pull request with the source diff, why the glyph is better, affected
families, and before/after evidence. Follow the release versioning guidance in
[DEVELOPMENT.md](DEVELOPMENT.md) when rebuilding fonts for a release. Use the
[coupon workflow](DEVELOPMENT.md#slice-validation) to provide slicer evidence
and record your line width, slicer version, profile, and any physical print test.

The preview checks thin ink, tight enclosed holes, gaps between separate pieces,
and spacing in the displayed line. Finishing fills negative space narrower than about 2w with
ink. The preview and validation compare that filled area with the original glyph and
warn in amber when an edit adds more than 0.5 w²; strokes moved closer than 2w then
print as solid ink. The warning does not fail validation, because acute joins such as
N, K and v are filled by design. All-family validation also detects glyphs
that disappear from Mono and tabular digits that exceed their width budget.
Maximum thickness and open tight regions are informational, consistent with
the current verification code; 3w dots and some joins exceed the original 2.85w
two-bead threshold. A green preview does **not** establish that every pair, TTF
rounding result, or sliced toolpath passes. The normal build and test suite remain
the acceptance gate.

## Scope

This first version adjusts existing numeric coordinates and radii. Adding or
removing strokes, changing endpoint types, new character coverage, and changing
construction topology still require editing Python. It does not generate new
TTFs or run OrcaSlicer in the browser. The preview uses source geometry; it is
not a screenshot of an installed font or a simulated print guarantee.

The local server accepts only bounded, finite numeric substitutions at cataloged
AST locations. It does not accept Python expressions or arbitrary file paths.
Geometry subprocesses have a timeout, and mutation-style API requests require a
per-session token and a local origin. These controls support a local development
tool; the server is not intended for public hosting.

## Interface assets

The interface follows the Gridline colors, pane structure, controls, and typography
from `thereprocase/thereprocase.github.io` at revision `94980f1`. IBM Plex Sans
(400/600) and IBM Plex Mono (400) Latin WOFF2 files are bundled from Fontsource
5.3.0; their SIL OFL notices are in `tuner/fonts/`. No Google Fonts request is
required at runtime.
