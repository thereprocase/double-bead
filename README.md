# Fillaprint

**v0.1.0 beta — fine-tuning for release.** Font shapes, spacing, and print behavior may change before 1.0. A future Nerd Fonts launch is a target; this beta is not part of Nerd Fonts.


**A typeface for FDM 3D printing. Strokes and gaps use the same minimum width.**

![Fillaprint: three font families for FDM printing, with dimensions and symbols.](showcase/hero.png)

Uniform stroke width does not control the width of the gaps inside and between
letters. When those gaps are narrower than the strokes, the background material
can become too thin to print while the strokes are still printable.

Fillaprint uses equal minimum widths for strokes and gaps. Both are
based on the extrusion line width. This gives the two materials the same design
minimum and reduces the label size needed to print the smallest features.

Three TrueType families. Free for personal and commercial use.

**[Try it in your browser](https://thereprocase.github.io/fillaprint/)** ·
**[Get the fonts](#get-the-fonts)** · **[Choose a size](#choose-a-print-size)** ·
**[License](#license)**

## Equal minimum widths for strokes and gaps

Let **w** be one extrusion line width. At the font's reference size:

- A normal stroke is **2w** wide: two lines of plastic side by side.
- A clear gap is **at least 2w** wide, including the spaces inside letters.
- Joins can be thicker. Some gaps are wider. The **minimum widths** match;
  the areas of ink and background can differ.

Rounded corners and thicker joins reduce thin wedges in the background material
that would be narrower than the intended extrusion width.

![The two-bead rule: an H with 2w strokes and a 3w gap. The minimum clear gap is 2w.](showcase/two-bead-rule.png)

Use the intended extrusion width when slicing, and check the resulting toolpaths
before printing.

## Applications

The first job was small, two-colour labels on masonry repointing keys. The font
now has upper- and lowercase letters, accents, fractions, arrows, and measurement
symbols. Use it for tool labels, bins, dimensions, and text on printed parts.

![Tool names, masonry measurements, dimensions, accented words, and fixed-width labels.](showcase/labels.png)

These images use the actual font outlines and spacing. They are digital
specimens, not photos of printed parts.

## Get the fonts

| Download | Use | Spacing |
| --- | --- | --- |
| [**Fillaprint**](fonts/Fillaprint-Regular.ttf?raw=true) | General labels | Letter widths vary; spacing adjusts between pairs |
| [**Fillaprint Tab**](fonts/FillaprintTab-Regular.ttf?raw=true) | Numbers in columns | Letter widths vary; digits have equal widths |
| [**Fillaprint Mono**](fonts/FillaprintMono-Regular.ttf?raw=true) | Fixed-width layouts | Every character uses a 12w cell |

[Download all three fonts and the license as a ZIP](https://thereprocase.github.io/fillaprint/downloads/Fillaprint-0.1.0-beta.zip).

Open a TTF file in your system's font installer. On Windows, you can also
right-click it and choose **Install**. Restart your CAD or design app if the font
does not appear.

To replace an older Windows install, see the optional
[installation script](tools/install_fonts.ps1). It can also remove registrations
for the old Double bead and Beadjoint names. Read its options before running it.

![Proportional text, equal-width digits in columns, and fixed-width text.](showcase/5-families.png)

Fillaprint and Tab each have **376 drawn characters**, plus space and
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

Increasing the text size widens both strokes and gaps and may add extrusion
paths. Below the reference size, their minimum widths are less than two
extrusion widths. The default line spacing accommodates accents and letters
that extend below the baseline.

[Size calculator](https://thereprocase.github.io/fillaprint/#size) ·
[Print settings and sizing details](docs/PRINTING.md)

## Recorded toolpaths

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

- **Commercial use.** You may sell parts, artwork, or documents made with the fonts. Those outputs do not need the OFL or a credit line.
- **Redistribution and modification.** Keep the copyright notice and OFL with any
  font files you distribute. Changed fonts must also use the OFL.
- **Reserved names.** To use the Reserved Font Names for a changed
  version, you need written permission.
- **Font sales.** The font cannot be sold by itself. The OFL allows it to be bundled with software.

Small fixes and large changes are both allowed. If you build on this font,
please say where it came from and what you changed. That is a request; the OFL
sets the legal terms.

[Full license](OFL.txt) · [License explained](docs/LICENSING.md)

---

Designed by [Repro](https://github.com/thereprocase). **Fillaprint** is a real name from a real human who has better ideas than me. And the whole "proportional negative space" idea is mine, seemed like a good idea. The glyphs though? Pure vibes, good luck. 
