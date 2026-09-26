Fillaprint v0.1.1 is a beta update of the typeface for small FDM-printed labels. We are fine-tuning the letterforms, spacing, and print behavior for release, with an eventual Nerd Fonts launch as a future target. This is not an official Nerd Fonts release.

Download **Fillaprint-0.1.1-beta.zip** for all three families, installation notes, and the SIL Open Font License 1.1. Internal OpenType version: **0.101**.

What changed since v0.1.0:

- **Dots are 3w across** instead of 2w (i, j, punctuation, dot and dieresis accents), so they keep a solid core when sliced. Affected advance widths and kerning changed; text set in v0.1.0 can reflow.
- **ĳ** is two letters again: v0.1.1 development builds printed it as one solid slab.
- **Fillaprint Mono** keeps every glyph, including the missing-glyph box, on its fixed cell, and uses the same J " - . / shapes as the other families.
- **Line spacing:** letters with a comma below (ș ț ķ ļ ņ ģ ŗ) stacked directly under accented capitals (Å Ă Š) need 30.6w line spacing instead of the default 28w to keep a 2w gap.
- **Contributing:** the repository now includes a local glyph tuner that previews and validates changes to the glyph sources and exports a Git patch.

[Try the font, calculate a print size, and view specimens](https://thereprocase.github.io/fillaprint/).

Nominal strokes and minimum clear gaps use two extrusion widths. Check your own sliced preview. The fonts were rebuilt from the tagged sources with the pinned dependencies; this release does not claim new physical-print validation.

Replace installed beta fonts and restart your design application when updating. Keep the v0.1.0 ZIP with projects that need its exact layout.

Licensed under SIL OFL 1.1 for personal and commercial use. License and copyright notices are included in the ZIP and embedded in each font.
