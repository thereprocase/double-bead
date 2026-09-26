# Building Fillaprint

Run commands from the repository root with Python 3.12 or newer and these packages:

```sh
python -m pip install -r requirements.txt
python build.py
python -m unittest discover -s tests
python tools/public_showcase.py
```

Some macOS/Linux installs only provide `python3` (no plain `python`); substitute it in
every command in this file if `python --version` fails or resolves to Python 2.

For reproducibility, build in a fresh virtual environment with the pinned versions
and compare your output with the committed binaries:

```sh
python -m venv .venv
# macOS / Linux:
. .venv/bin/activate
# Windows PowerShell (if this is blocked, run once: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned):
# .venv\Scripts\Activate.ps1
# Windows cmd.exe:
# .venv\Scripts\activate.bat
python -m pip install --only-binary=:all: -r requirements.txt
python build.py && python -m unittest discover -s tests
git status --short fonts/        # empty when your build matches the committed fonts
```

Only a Linux build (with glibc) matches the committed fonts byte for byte; macOS and Windows
finish a few glyphs differently (see [Platforms](#platforms)).

The TTFs depend on the fontTools version as well as the glyph sources: the same sources
built with a different fontTools give different bytes. Keep `requirements.txt` pinned and
rebuild the fonts in the same commit whenever the pins or the sources change.

Font timestamps are fixed to remove clock-dependent differences: `head.created` and `modified`
come from `BUILD_DATE` in `beadjoint/release.py`, or from `SOURCE_DATE_EPOCH` when that
environment variable is set. Bump `BUILD_DATE` together with `VERSION` for each release
(see [RELEASING.md](RELEASING.md)).

The v0.1.1 fonts were built in a fresh virtual environment with exactly the pinned
requirements. Two independent builds from a clean export produced byte-identical TTFs, and
CI rebuilds the fonts on every push and fails if `fonts/` changes. The pinned environment
has no `uharfbuzz`, so fontTools packs the GPOS kerning with its pure-Python serializer;
installing `uharfbuzz` switches it to the HarfBuzz repacker, which lays the same kerning out
in different bytes. The fonts committed before v0.1.1 appear to have been packed that way:
re-serialising their GPOS with the pure-Python packer does not reproduce their bytes, and
clean rebuilds differed from them by about 116 bytes of GPOS while every pair adjustment
matched.
Build releases with exactly `requirements.txt`, and compare behaviour as well as hashes
before concluding that a rebuild differs.

The build writes three TTFs, their OFL license, specimen images, and `report.json`.
It exits unsuccessfully if geometry, outline read-back, spacing, or setting fidelity
checks fail. See [SPEC.md](SPEC.md) for tolerances and construction rules.

The public showcase script reads the released TTF outlines and their kerning. It
does not redraw or approximate the letters. It creates `showcase/hero.png`,
`showcase/two-bead-rule.png`, and `showcase/labels.png`.

The older `tools/showcase.py` produces the full glyph, language, symbol, and family
sheets. Its final slicer panel additionally requires `site/dist/crops/`, generated
from the companion demo workflow. The committed `showcase/6-sliced.png` is a
toolpath visualization from that workflow, not a photograph or a new slicing run.

## Platforms

Releases are built on Linux x86-64, where CI rebuilds the committed fonts byte for byte.
Linux with glibc reproduces that build's glyph geometry exactly: CI found x86-64 and aarch64
with glibc 2.39 identical, and so was an x86-64 build with glibc 2.44. macOS and Windows do
not, with the same pinned packages (shapely 2.1.2 with GEOS 3.13.1, numpy 2.5.3, scipy
1.18.1). Their C math libraries round `sin`, `cos`, `tan`, `acos` and `atan2` differently
from glibc in the last one to three bits for some arguments. Those functions place the
vertices of the fillet arcs (`geom.fillet`, through Python's `math`) and of GEOS's round
buffers, so most glyph coordinates differ in their last bits before finishing. Mostly that
is harmless, but where edges touch or nearly touch, those bits decide whether a hairline
sliver joins two pockets of negative space or a crack opens where two fillet arcs meet,
and finishing (`geom.finish`) decides by area which pockets to fill. CI measured:

| Platform | Glyphs | Distance from the release outline |
| --- | --- | --- |
| Windows | Mono 6, 8, e ę ĕ ě ē é è ė ê ë | 0.205 to 0.213 w; in 6, two 0.054 w² corner pockets join into one 0.108 w² pocket, over the 0.1 w² fill threshold |
| Windows | Å, Ů | the ring's top 2.1e-5 w higher: a crack where two of its fillet arcs meet is filled |
| macOS, Apple silicon and Intel | Mono z ź ż ž | 0.045 to 0.048 w: a 0.103 w² sliver along the diagonal is filled |

Every other glyph stays within the 0.03 w build tolerance of the release, and Python 3.12
and 3.14 give identical results on each platform. The tests therefore compare the committed
fonts with the local geometry at 0.03 w only on Linux with glibc and allow 0.25 w elsewhere;
the line-spacing band test likewise allows 1e-4 w instead of 1e-6 w. CI runs the full suite
on Linux, macOS and Windows. Fonts built on macOS or Windows differ from the release in the
glyphs above, so build releases on Linux. The glyph tuner's previews show the local geometry
and differ from the release in the same way.

## Glyph tuner

For contribution editing, run `python -m tuner.serve`. The localhost tuner edits
source coordinates in memory, previews the real geometry, validates affected
glyphs, and exports a Git patch. See [TUNER.md](TUNER.md) for its workflow and limits.

## Browser specimen

```sh
python site/build_site.py
python site/serve.py
```

`site/build_site.py` reads `review/LOG.md` and `review/notes.json` as live inputs;
the rest of `review/` is frozen design history that may not run against the
current package. `site/serve.py` binds to `127.0.0.1` by default; pass
`--host 0.0.0.0` (and open the matching firewall rule) to also serve the LAN.

The static site is written to `site/dist/` and served on port 8765. It includes a
size calculator, glyph browser, and downloadable fonts with their license.
Toolpath crops are optional inputs; see the build script's `--demo` and `--crops`
arguments. Without them, the site does not provide new slicing evidence.

## Slice validation

`demo/demo_plate.py` and `demo/demo_check.py` build and slice a two-face coupon,
then score how every glyph printed from the gcode. They need two things beyond
`requirements.txt`:

- [CadQuery](https://cadquery.readthedocs.io/) (`python -m pip install cadquery`) to
  build the coupon solids.
- [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer). The scripts find it on `PATH`
  as `orca-slicer`, or use the `ORCA_SLICER` environment variable.

```sh
python demo/demo_plate.py                  # slice demo/slice with demo/profiles
python demo/demo_check.py                  # score it; writes demo/check.json
demo/tune.sh classic wall_generator=classic   # slice + score one override set
demo/tune_all.sh                           # a batch of wall variants, then rank them
demo/tune_all2.sh                          # follow-up: bead-width steps at angle=30, plus two angle comparisons
```

`demo/slicer_support.py` holds the 3MF writing, OrcaSlicer lookup and gcode parsing.
The starter presets in `demo/profiles/` are explained in its README. They are not the
exact profile behind the committed showcase; that setup is recorded in
[PRINTING.md](PRINTING.md).

## Repository layout

| Path | Contents |
| --- | --- |
| `fonts/` | Installable TTFs and OFL license |
| `beadjoint/` | Original glyph geometry, spacing, checks, and TTF writer |
| `docs/SPEC.md` | Reproducible construction specification |
| `showcase/`, `specimen/` | Font specimens and explanatory images |
| `site/` | Browser specimen and size calculator |
| `demo/` | Coupon generation and slicer checks |
| `tests/` | Unit tests (`python -m unittest discover -s tests`) |
| `tools/` | Showcase image generation and font installers |
| `review/` | Historical scripts are frozen design history and may not run against the current package; `LOG.md` and `notes.json` are still read live by `site/build_site.py` |
| `tuner/` | Local Gridline interface for source-coordinate contributions |

The Python package retains the working name *Beadjoint*. The public family name
is *Fillaprint*.

## Release versions

See [RELEASING.md](RELEASING.md) for the packaging and publishing procedure.

The first Fillaprint release is **v0.1.0 beta**, with OpenType version **0.100**.
Use immutable tagged releases and versioned ZIPs; do not replace an existing release's binaries.
The family names stay Fillaprint, Fillaprint Tab, and Fillaprint Mono for compatible updates.
Increment the release version and internal font revision for every changed build.
For beta patches, v0.1.1 maps to 0.101; v0.2.0 maps to 0.200; v1.0.0 maps to 1.000.
Record changes to outlines, advances, kerning, coverage, and print guidance in release notes.
Users should replace the old installed fonts and restart their CAD/design application.
Existing documents can reflow with a changed font; retain the matching release ZIP
with a project or preserve final lettering as outlines when exact geometry matters.

We are fine-tuning the beta for release and eventually targeting a Nerd Fonts launch.
That requires separate patching and upstream review. Added icon glyphs must not be
assumed to satisfy Fillaprint's two-bead print geometry.
