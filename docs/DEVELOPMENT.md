# Building Fillaprint

Run commands from the repository root with Python 3.12 or newer and these packages:

```sh
python -m pip install -r requirements.txt
python build.py
python -m unittest discover -s tests
python tools/public_showcase.py
```

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

## Browser specimen

```sh
python site/build_site.py
python site/serve.py
```

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
| `review/` | Design history and review evidence |

The Python package retains the working name *Beadjoint*. The public family name
is *Fillaprint*.

## Release versions

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
