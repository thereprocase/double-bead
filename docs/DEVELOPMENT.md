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

Linux builds with glibc 2.39 and 2.44 (x86-64) matched the committed fonts byte for byte;
macOS and Windows builds do not, because a few glyphs finish differently there (see
[Platforms](#platforms)).

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

Releases are built on Linux x86-64, where CI rebuilds the committed fonts byte for byte. The
glyph geometry was found identical on Linux with glibc 2.39 (x86-64 and aarch64, in CI) and
glibc 2.44 (x86-64); other glibc versions, architectures and CPUs are unverified. The tests
treat every Linux with glibc as the reference, so one whose geometry differs fails the exact
checks instead of quietly taking looser ones. CI's Linux jobs run on the `ubuntu-24.04` image
(glibc 2.39) rather than `ubuntu-latest`, so the reference does not move to a new glibc
unannounced; change the image in a commit of its own and check that its build still matches
the committed fonts.

macOS and Windows differ, with the same pinned packages (shapely 2.1.2 with GEOS 3.13.1,
numpy 2.5.3, scipy 1.18.1). Their C math libraries round `sin`, `cos`, `tan`, `acos` and
`atan2` differently from glibc in the last one to three bits for some arguments. Those
functions place the vertices of the fillet arcs (`geom.fillet`, through Python's `math`) and
of GEOS's round buffers, so most glyph coordinates differ in their last bits. Mostly that is
harmless, but where arcs meet at a mitre join, or edges touch or nearly touch, those bits
can move a peak, decide whether a hairline sliver joins two pockets of negative space, or
open a crack, and finishing (`geom.finish`) decides by area which pockets to fill. CI measured
on macOS 26.6 (arm64), macOS 15.7 (Intel) and Windows Server 2025 (10.0.26100):

| Platform | Glyphs | Difference from the release |
| --- | --- | --- |
| Windows | Mono 6, 8, e ę ĕ ě ē é è ė ê ë | outline 0.205 to 0.213 w off; in 6, two 0.054 w² corner pockets join into one 0.108 w² pocket, over the 0.1 w² fill threshold |
| Windows | Å, Ů | the ring's top 8.3e-5 w higher, where two of its fillet arcs meet; this is already in the composed glyph, before finishing |
| macOS, Apple silicon and Intel | Mono z ź ż ž | outline 0.045 to 0.048 w off: a 0.103 w² sliver along the diagonal is filled |

Every other glyph stays within the 0.03 w build tolerance of the release, and Python 3.12
and 3.14 give identical results on each platform. On the reference the tests compare the
committed fonts with the local geometry at 0.03 w and allow ink 1e-6 w past the line-spacing
band. Elsewhere they use the slack measured on these images, with headroom:

| Platform | Outline distance | Glyphs per family beyond 0.03 w | Band |
| --- | --- | --- | --- |
| macOS | 0.06 w (measured 0.048) | 8 (measured 4) | 1e-6 w (measured 0) |
| Windows | 0.25 w (measured 0.213) | 24 (measured 12) | 2.5e-4 w (measured 8.3e-5) |
| any other platform | 0.03 w | 0 | 1e-6 w |

The glyph count keeps a change to many glyphs failing there: making the dots 2 % larger
(`DOT` 1.5 to 1.53) moves 40 or 41 glyphs per family by up to 0.126 w. Fonts built on macOS or
Windows differ from the release in the glyphs above, so build releases on Linux. The glyph
tuner's previews show the local geometry and differ from the release in the same way.

## Continuous integration

`.github/workflows/test.yml` runs on every push to `main` and every pull request:

- **test**: the whole suite on Linux, macOS and Windows with Python 3.12 and 3.14, against
  the committed fonts, with the tolerances described under [Platforms](#platforms).
- **build fonts from sources**: on Linux with Python 3.12, `python build.py` builds the fonts
  from the checked-out sources and runs its own geometry and read-back checks; then
  `tests/test_beadjoint.py` and `tests/test_release.py` run against the fonts it just built,
  at the exact tolerances and with nothing skipped; finally the committed `fonts/` is compared
  with that build.

The jobs run on pinned images rather than the `-latest` labels, which move without a commit
here: `ubuntu-24.04` (glibc 2.39, the reference), and `macos-26` (arm64) and `windows-2025`,
the images the macOS and Windows slack was measured on. A newer image can round differently,
so move to one in a commit of its own, and on Linux check that the build still matches the
committed fonts. The Linux jobs set `FILLAPRINT_REQUIRE_REFERENCE=1`, and a test fails if that
image is not the reference platform, rather than letting it take another platform's slack.

**On `main`** no committed-font test is skipped (the Windows jobs still skip the one test that
needs POSIX signals), and the build job fails unless the committed fonts match the build byte
for byte.

**On pull requests**, which are source-only ([TUNER.md](TUNER.md#contribute)), the committed
fonts may predate the sources. The workflow sets `FILLAPRINT_COMMITTED_FONTS_MAY_BE_STALE=1`
in the test matrix, which skips exactly the seven tests that compare the committed fonts with
the sources or with constants taken from them:

| Test | Compares the committed fonts with |
| --- | --- |
| `test_beadjoint.Fonts.test_outlines_follow_source` | the finished glyph geometry |
| `test_beadjoint.Fonts.test_mono_lines_follow_setting` | the setting engine's Mono lines |
| `test_beadjoint.Fonts.test_mono_fixed_pitch` | `CELL_M` and `LINE_MIN` |
| `test_beadjoint.Fonts.test_tab_figure_cells` | `CELL_F` and `LINE_MIN` |
| `test_beadjoint.LineSpacing.test_ink_band_in_fonts` | the band and its comma-below letters |
| `test_beadjoint.Licensing.test_fonts_carry_license` | `beadjoint/licensing.py` and `OFL.txt` |
| `test_release.FontVersions.test_name_id_5` | `VERSION` in `beadjoint/release.py` |

The log names each skip and its reason, and every other test runs as on `main`. A test fails
if the variable is set in a GitHub run that is not a pull request. The build job runs all
seven on the fonts built from the pull request's sources. If the committed fonts differ from
that build and the pull request leaves `fonts/` as it is on the base branch, the job posts a
notice and a job summary and passes. If the pull request changes `fonts/` and they still
differ from the build, it fails: the fonts were rebuilt wrongly (for example on macOS or
Windows, or with a different environment). Locally the variable is unset and nothing skips.

A source-only pull request lands on `main` in one of two ways, and either way `main` gets
the sources and the matching fonts in the same push:

- rebuild on the pull request's branch before merging: `python build.py` on Linux in the
  pinned environment ([RELEASING.md](RELEASING.md) step 3), then commit `fonts/`, the specimen
  images and `report.json`; the build job then requires the fonts to match;
- or merge locally, rebuild the same way, commit, and push the merge and the rebuild
  together.

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
