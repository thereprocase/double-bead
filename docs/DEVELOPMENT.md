# Building Brewster Technical

Run commands from the repository root with Python 3.12 or newer and these packages:

```sh
python -m pip install shapely fontTools numpy scipy Pillow
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

`demo/demo_plate.py` and `demo/demo_check.py` build and slice a two-face coupon.
They require OrcaSlicer and helpers/profile data from the author's companion
masonry-keys project. They are not standalone commands for a fresh clone.
The recorded tested profile is described in [PRINTING.md](PRINTING.md).

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
is *Brewster Technical*.
