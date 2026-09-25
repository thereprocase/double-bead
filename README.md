# Brewster Technical

**A typeface for FDM 3D printing. Strokes and gaps use the same minimum width.**

![Brewster Technical: three font families for FDM printing, with dimensions and symbols.](showcase/hero.png)

A font can have even strokes and still be hard to print. The strokes fit. The
small space inside an **e** does not. On a two-colour part, even the “empty” space
is full of plastic.

Brewster Technical gives the ink and the negative space a **1:1 minimum width**.
Both start from the extrusion line width. The aim is for the small features to
reach the print limit together. Large features should not waste space while a
small gap runs out of room for plastic.

Three TrueType families. Free for personal and commercial use.

**[Try it in your browser](https://thereprocase.github.io/brewster-technical/)** ·
**[Get the fonts](#get-the-fonts)** · **[Choose a size](#choose-a-print-size)** ·
**[License](#license)**

## The gaps need plastic too

Let **w** be one extrusion line width. At the font's reference size:

- A normal stroke is **2w** wide: two lines of plastic side by side.
- A clear gap is **at least 2w** wide, including the spaces inside letters.
- Joins can be thicker. Some gaps are wider. The **minimum widths** match;
  this is not a promise of equal areas of ink and background.

This keeps a narrow gap from setting the size of the whole label. Rounded
corners and thicker joins also help avoid thin wedges of space that the nozzle
cannot fill.

![The two-bead rule: an H with 2w strokes and a 3w gap. The minimum clear gap is 2w.](showcase/two-bead-rule.png)

The drawing gives the slicer room to work. Check the sliced preview before you
print. A font file cannot set your extrusion width for you.

## What it is for

The first job was small, two-colour labels on masonry repointing keys. The font
now has upper- and lowercase letters, accents, fractions, arrows, and measurement
symbols. Use it for tool labels, bins, dimensions, and text on printed parts.

![Tool names, masonry measurements, dimensions, accented words, and fixed-width labels.](showcase/labels.png)

These images use the actual font outlines and spacing. They are digital
specimens, not photos of printed parts.

## Get the fonts

| Download | Use | Spacing |
| --- | --- | --- |
| [**Brewster Technical**](fonts/BrewsterTechnical-Regular.ttf?raw=true) | General labels | Letter widths vary; spacing adjusts between pairs |
| [**Brewster Technical Tab**](fonts/BrewsterTechnicalTab-Regular.ttf?raw=true) | Numbers in columns | Letter widths vary; digits have equal widths |
| [**Brewster Technical Mono**](fonts/BrewsterTechnicalMono-Regular.ttf?raw=true) | Fixed-width layouts | Every character uses a 12w cell |

[Download all three fonts and the license as a ZIP](https://thereprocase.github.io/brewster-technical/downloads/BrewsterTechnical-1.201.zip).

Open a TTF file in your system's font installer. On Windows, you can also
right-click it and choose **Install**. Restart your CAD or design app if the font
does not appear.

To replace an older Windows install, see the optional
[installation script](tools/install_fonts.ps1). It can also remove registrations
for the old Double bead and Beadjoint names. Read its options before running it.

![Proportional text, equal-width digits in columns, and fixed-width text.](showcase/5-families.png)

Brewster Technical and Tab each have **376 drawn characters**, plus space and
alternate character mappings. Mono has **362**. It narrows some shapes and leaves
out 14 that do not fit its cell. Tab has a figure space (U+2007): a blank as wide
as a digit.

The fonts cover ASCII, Latin-1, Latin Extended-A, Romanian comma-below letters,
extra Welsh accents, capital ẞ, curly quotes, fractions, currency signs, arrows,
and selected math symbols. They do not cover full Greek or Cyrillic alphabets.

[All characters](showcase/2-all-glyphs.png) ·
[Language samples](showcase/3-languages.png) ·
[Symbols and figures](showcase/4-symbols.png)

## Choose a print size

Use the **extrusion line width** set for the text in your slicer. This can differ
from the nozzle diameter. Call it **w**.

| Measurement | Formula | w = 0.32 mm | w = 0.42 mm |
| --- | --- | --- | --- |
| Capital height / Fusion text Height | **14 × w** | **4.48 mm** | **5.88 mm** |
| Em-based font size | 20 × w | 6.40 mm | 8.40 mm |
| Normal stroke / minimum clear gap | 2 × w | 0.64 mm | 0.84 mm |
| Default distance between baselines | 28 × w | 8.96 mm | 11.76 mm |

For a **0.42 mm** line width, start with **5.88 mm** capital letters. In Fusion,
enter that as the text **Height**. If your app sizes text by the em, use
**8.40 mm**. These are two ways to size the same letters. If the app is unclear,
convert an **H** to outlines and measure its height.

Larger text gives the slicer more room and may add lines of plastic. Smaller
text loses the two-line margin. Keep the default line spacing to leave room for
accents and letters that extend below the baseline.

[Size calculator](https://thereprocase.github.io/brewster-technical/#size) ·
[Print settings and sizing details](docs/PRINTING.md)

## What the slicer sees

![Recorded OrcaSlicer Arachne toolpaths for letters and symbols.](showcase/6-sliced.png)

This is the top face of a test piece, sliced with OrcaSlicer's Arachne wall
generator at **w = 0.32 mm**. Yellow is letter plastic. Grey is body plastic.
Blue is the design outline. White marks areas with no line of plastic on that
layer. This is a toolpath render, not a photo.

The build tools check stroke shapes, spacing, and outlines read back from the
TTFs. The test-piece tools also measure where sliced paths fill the design,
leave gaps, or cross an edge. See the [design specification](docs/SPEC.md) and
[build instructions](docs/DEVELOPMENT.md) for the checks and their limits.

## License

The fonts use **SIL Open Font License 1.1**, with the family names reserved.

- **Use them in commercial work.** Sell the parts, artwork, or documents you
  make. Those outputs do not need the OFL or a credit line.
- **Share and change the fonts.** Keep the copyright notice and OFL with any
  font files you distribute. Changed fonts must also use the OFL.
- **Rename changed versions.** To use the Reserved Font Names for a changed
  version, you need written permission.
- **Do not sell the font by itself.** The OFL allows it to be bundled with software.

Small fixes and large changes are both allowed. If you build on this font,
please say where it came from and what you changed. That is a request; the OFL
sets the legal terms.

[Full license](OFL.txt) · [License explained](docs/LICENSING.md)

---

Designed by [Repro](https://github.com/thereprocase). **Brewster Technical** is a
family tribute. It was first called **Double bead**, for two lines of plastic
laid side by side. An earlier name, **Beadjoint**, refers to a mortar-joint
profile. That name remains on the Python package; `double-bead` remains in the
repository URL.
