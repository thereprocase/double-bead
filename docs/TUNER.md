# Local glyph tuner

The tuner edits numeric parameters in the **existing Python source**. It uses the
same constructors, finishing filters, accent composition, spacing engine, and
geometry checks as the font build. It exports ordinary Git patches, with no
second glyph format to maintain.

## Start

From a clone of this repository, using Python 3.12 or newer. On macOS and Linux:

```sh
python -m venv .venv          # use python3 if python is not found
. .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.txt
python -m tuner.serve
```

On Windows, in PowerShell:

```powershell
py -3.12 -m venv .venv        # or: python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --only-binary=:all: -r requirements.txt
python -m tuner.serve
```

PowerShell's default execution policy blocks `Activate.ps1`. Allow local scripts
once with `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use cmd
instead, where the activation command is `.venv\Scripts\activate.bat`.

Open **http://127.0.0.1:8766** if the browser does not open automatically. Use
`--port 8767` to choose another port or `--no-browser` to suppress opening a tab.
The server binds only to the local loopback interface. There are no accounts,
remote services, JavaScript packages, or additional Python dependencies. Bundled
IBM Plex fonts keep the Gridline interface available offline.

The repository keeps Python sources with LF line endings on every platform
(`.gitattributes`). The tuner hashes and edits those files byte for byte, so it
refuses to start on a checkout with Windows (CRLF) line endings and prints the
command that checks the sources out again.

Expect roughly these waits on a typical laptop: 8 to 12 s for the first preview
after starting the tuner, 1.5 to 3.5 s for later previews, a few seconds more for
the first preview in another family, and 5 to 30 s for all-family validation,
depending on how many glyphs the edit changes. A counter next to the status line
shows the seconds while it works, and repeated states (undo, redo, switching
back) come from a cache.

## Tune

1. Select a construction in the left rail. The catalog exposes
   **COUNT_CONSTRUCTIONS constructions and COUNT_PARAMETERS numeric
   parameters**, including base letters, capitals, symbols, Mono variants,
   accents, and the shared dot radius. Search by character or group name; exact
   character matches come first, and a letter drawn by a shared helper finds it
   too (`W` finds the Shared M / W construction). Accented characters have no
   construction of their own: searching `ñ` explains that it is built from `n` +
   tilde and offers both constructions, previewing `ñ`.
2. Drag the yellow construction points or edit exact numbers in the right rail.
   Hovering a point names it the way the fields do (`S1 point 3`, or
   `diagonal3 x₀, y₀` for the end of a diagonal) and highlights its fields;
   hovering or focusing a field highlights its point. On a touch screen, tap a
   field to find its point. The grid is numbered every 2w. Coordinates use `w`
   units and Y points down; a normal stroke stays **2w** wide. A short legend
   above the fields explains the constructors: `S` is an open stroke through its
   points, `So` a closed stroke, `D` a disk, `Rect` a rectangle, and `diagonal` a
   straight stroke between two points cut flat on the cap line and baseline.
   Their numbers count shapes in reading order on the source line.
3. Coordinates accept -32 to 32w and radii 0 to 8w (wider where the source
   value already is). A value outside the range, or an emptied field, is put
   back to the current value with a message on that row.
4. Inspect the original and edited outlines, a sample word or phrase, and the
   geometry readouts. The line-width field only converts dimensions to mm. The
   status line turns red when the previewed glyph fails a check or the sample
   line has a gap below 2w, and amber for the finishing-fill warning described
   below.
5. Change the preview glyph to a derived character (for example `ñ` while
   editing the base `n`) or switch family. Base edits propagate through the
   real constructors; independent Mono replacements remain independent.
6. Run **Validate changed glyphs**. This compares all three families with the
   unmodified source and checks changed outlines, including derived accents.
   Problems are listed in a red block. Each changed glyph gets a chip: red for a
   failure, dashed red for a glyph that dropped out of a family (for example
   `M:n dropped from Mono`), amber for a fill warning, green for a pass. Select a
   chip to preview that glyph. Results stay visible when you change the preview
   or edit, marked as results for earlier settings or edits until you
   revalidate; undoing back to the validated edits clears the mark. Validation
   builds the previewed glyph first. When that glyph cannot be built, the block
   says **Validation could not run** with the reason, and offers **Validate with
   the preview in Proportional** (Proportional has every character, and Tab and
   Mono are still checked) or **Undo the last change**.
7. Export a Git patch. If the current edits have not been validated, the page
   says so and offers **Validate now** or **Export anyway** instead of
   downloading; if validation found problems, it offers **Show the problems** or
   **Export anyway**. The browser saves `fillaprint-glyphs.patch` in its
   download folder.

Undo, redo, and reset are available. **Save session** writes a JSON file to share
or resume the parameter choices, and **Open session** reads one back. Opening a
file that is not a session, or one made for other source files, leaves your
current edits and preview untouched and explains why.

Session files contain repo-relative parameter identifiers, source hashes, the
checkout's Git commit when the server can read it, and numeric edits. They do not
include the preview phrase, local filesystem paths, usernames, machine details,
or Git credentials. Nothing is uploaded by the tuner.

The browser also autosaves the edits. Autosave belongs to one browser and one
exact address: `http://127.0.0.1:8766`, `http://localhost:8766`, and another
port each keep separate edits. After a reload, restored edits are announced,
the first edited construction is selected, and edited constructions carry a
badge in the left rail. Closing or reloading the tab does not ask for
confirmation, because autosave keeps the edits. If another tuner tab changes the
autosaved edits, this tab stops autosaving and asks whether to load the other
tab's edits or keep its own; until you choose, edits made in this tab exist only
in the page, and the browser asks before you leave it. If the autosaved edits
belong to different source files, they are downloaded as
`fillaprint-previous-session.json` and the tuner starts without them.

The server never edits your source files. Sessions contain source SHA-256 hashes
and are rejected when opened against different source files; the message names
the commit the session was saved at when it knows it. If you edit Python in
another editor, restart the tuner. Applying a patch to a newer checkout is a
normal Git review/rebase operation; the tuner does not guess at changed offsets.

Construction points can coincide. Moving one does not automatically move the
other; use the numeric fields to edit both. Points are not shown for accent
marks, Mono constructions, shared helpers, or constructions that pass through
helper transforms, because their raw points do not sit in the final glyph's
coordinate system; the right rail says which case applies. They are also hidden
while the preview shows a different glyph or family than the construction, with
a button to show the construction again. While a preview is stale or has
failed, the drawing, readouts, and sample line are dimmed, the outline pane is
tagged **Stale** or **Failed**, and dragging pauses until the preview is current.

## Messages

- *Can't reach the tuner server — is python -m tuner.serve still running?* The
  server process stopped. Start it again and select **Retry**, or reload; autosave
  keeps the edits.
- *Reload the local tuner page.* The server restarted. Select **Reload page**;
  autosave keeps the edits.
- *beadjoint/glyphs.py changed on disk since the tuner started, so earlier
  previews no longer apply. Restart the tuner to load the current files.* (The
  message names the files that changed.) Python files changed after the tuner
  started, for example by `git apply`. Stop the tuner, start it again, then
  select **Reload page**.
- *Another tuner tab is computing (or this page before a reload) — retrying…*
  The server computes one preview at a time. The page retries for about a
  minute, then offers **Retry**.
- *The tuner has too many open connections. Try again shortly.* The page
  retries previews on its own for about a minute (*The tuner server has too many
  open connections — retrying…*), then offers **Retry**; a failed export or
  validation offers **Retry** as well. Closing other tuner tabs helps.
- *Mono leaves out n: after this edit its ink is wider (10.50w) than Mono's 10w
  limit. Narrow the glyph, or undo the last change.* The edit made the previewed
  glyph too wide for Mono; the message gives the new width. Select **Undo** or
  **Preview in Proportional**.
- *Mono doesn't include ŉ: wider than Mono's 10w limit. Preview it in
  Proportional or Tab.* With edits present the message reads *Mono doesn't
  include ŉ before this edit (wider than Mono's 10w limit), and it still doesn't
  fit after it. Preview it in Proportional or Tab.* The glyph is not in Mono
  even before your edit. Select **Preview in Proportional**.
- Messages that name a construction or a glyph (with its family in brackets)
  and a problem come from values the geometry cannot use, for example *n (Base):
  the rounded corners at (1, 1) and (6, 1) together need 9w of a segment only
  5w long. Reduce the corner radius or lengthen the segment.*, *. (Proportional):
  the edit leaves no ink to print.*, or *a (Proportional): the edit leaves an
  outline that is not a valid shape (it crosses itself).* Select **Undo** or
  change the value.
- *ĳ (Proportional): finishing joined separate pieces — keep them at least
  1.98w apart; it is 5.5w thick at its thickest; the fonts allow at most
  4.85w.* The glyph fails a check the font build also enforces, so
  `python build.py` would reject it. Finishing fills gaps narrower than about
  2w with ink: pieces the source keeps apart, such as the two parts of ĳ or a
  dot over its stem, merge once they come closer than 1.98w. The build also
  rejects ink thicker than 4.85w. The message lists only the problems that
  apply; the other print checks read the same way (*it has ink narrower than
  2w, which cannot print*, *it encloses a hole narrower than 2w*, *separate
  pieces are only 1.5w apart (at least 1.98w)*). Move the pieces or strokes
  apart until the status line clears, or select **Undo**. Joins the design
  intends, such as Mono's k, are allowed.
- *0 (Tab) is 8.50w wide. Tab gives every digit the same 9w cell, so a digit
  wider than 7.02w comes closer than 1.98w to its neighbours.* Narrow the digit
  or undo the change.
- *The preview took longer than 3 minutes and was stopped. Undo the last change,
  or try again.* Select **Retry**, or undo if the last value made the geometry
  hard to build.
- *That file is not a tuner session.* The opened file is not a session JSON.
- *This session was saved for different glyph source files than this checkout
  has.* When the session records its commit, the message gives the command to
  check that commit out (`git switch --detach` followed by the commit), after
  which you restart the tuner.

## Contribute

Stop the tuner (Ctrl+C) before applying the patch: `git apply` changes the
sources it loaded. Then, from the repository root:

```sh
git switch -c glyph/my-adjustment
git apply --check ~/Downloads/fillaprint-glyphs.patch
git apply ~/Downloads/fillaprint-glyphs.patch
python build.py
python -m unittest discover -s tests
git restore fonts specimen report.json
git status --short
git diff -- beadjoint/
```

Replace `~/Downloads/fillaprint-glyphs.patch` with the path in your browser's
download folder; in Windows PowerShell that is usually
`$HOME\Downloads\fillaprint-glyphs.patch`. Start the tuner again afterwards if
you keep tuning. The applied edits are now part of the sources, so the old
autosave no longer matches; it is saved as `fillaprint-previous-session.json`
and the tuner starts without edits.

Contributor pull requests are source-only. `python build.py` and the tests must
pass, but the fonts, specimen images, and `report.json` they rewrite differ from
machine to machine; maintainers rebuild them once per release in the pinned
environment. `git restore fonts specimen report.json` discards those outputs, and
`git status --short` should then list only files under `beadjoint/`.

Open a pull request with the source diff, why the glyph is better, affected
families, and before/after evidence. Use the
[coupon workflow](DEVELOPMENT.md#slice-validation) to provide slicer evidence
and record your line width, slicer version, profile, and any physical print test.
Maintainers follow the release guidance in [DEVELOPMENT.md](DEVELOPMENT.md) when
they rebuild the fonts.

The preview checks thin ink, tight enclosed holes, gaps between separate pieces,
and spacing in the displayed line. Like the font build, it also fails a glyph
whose ink is thicker than 4.85w or whose separate pieces finishing joined (joins
the design intends, such as Mono's k, excepted). Finishing fills negative space narrower than about 2w with
ink. The preview and validation compare that filled area with the original glyph and
warn in amber when an edit adds more than 0.5 w²; strokes moved closer than 2w then
print as solid ink. The warning does not fail validation, because acute joins such as
N, K and v are filled by design. All-family validation also detects glyphs
that disappear from Mono and tabular digits that exceed their width budget.
Thickness between the original 2.85w two-bead threshold and the 4.85w limit, and
open tight regions, are informational, consistent with the current verification
code; 3w dots and some joins exceed 2.85w. A passing validation does **not** establish that every pair, TTF
rounding result, or sliced toolpath passes. The normal build and test suite remain
the acceptance gate.

## Scope

This first version adjusts existing numeric coordinates and radii written
directly in `S`, `So`, `D`, `Rect`, and `diagonal` calls inside the cataloged
construction functions, plus the shared dot radius. Numbers that reach a glyph
through other code are not exposed: arguments to helper transforms such as
shift, mirror, rotate, and spokes, the accent anchor and placement tables, the
internals of mark helpers such as the cedilla and ogonek, and other named
constants. The right
rail says when a construction passes through helper transforms, and a search
for an accented character names any mark drawn by such a helper. Adding or
removing strokes, changing endpoint types, new character
coverage, and changing construction topology still require editing Python. It
does not generate new TTFs or run OrcaSlicer in the browser. The preview uses
source geometry; it is not a screenshot of an installed font or a simulated
print guarantee.

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
