# Beadjoint

A font for multi-colour FDM text. Every stroke is exactly two extrusion widths, so an Arachne slicer
prints each stroke as one wall loop passing itself: no hairlines, no one-bead strokes, no gap fill.
The name: a bead is both an FDM extrusion and a mortar-joint profile, and the font was drawn for the
labels on masonry repointing keys.

It follows the two-bead font specification in [docs/SPEC.md](docs/SPEC.md) (lowercase, figures, the
optical spacing and the checks), extended to 376 glyphs: A-Z, all ASCII symbols, Latin-1, Latin
Extended-A, Romanian comma-below letters, Welsh ẁ ẃ ẅ ỳ, capital ẞ, dashes, curly quotes, primes, euro,
lira, florin, trade mark, fractions (halves, thirds, quarters, eighths), superscripts, arrows and
≤ ≥ ≈ ≠. Every common European keyboard layout and Latin-script European language is covered.

## Size it from your line width

The font is drawn in line widths (w). Take w from the line width your slicer uses for the outer wall
and top surface. Then:

| What you set | Value | At w = 0.32 mm | At w = 0.42 mm |
|---|---|---|---|
| **Fusion text Height** (Fusion sizes text by cap height) | **14 × w** | **4.48 mm** | 5.88 mm |
| Font size in programs that size by em (CadQuery, Inkscape, OpenSCAD, most slicers) | 20 × w | 6.40 mm | 8.40 mm |
| Font size in points | 20 × w ÷ 0.3528 | 18.1 pt | 23.8 pt |
| Stroke | 2 × w | 0.64 mm | 0.84 mm |
| x-height | 10 × w | 3.20 mm | 4.20 mm |
| Line pitch (the fonts' default) | 28 × w | 8.96 mm | 11.76 mm |

Line pitch: the fonts ask for 28 w baseline to baseline, which keeps accents, brackets and commas
2 w clear of the line above in any text (round 2 measured: g over ( needs 22 w, p over Á 26.4 w,
g over Å 28 w; a comma-below directly over a capital accent needs 31 w). 20 w is safe only for
unaccented text without brackets or descenders over capitals, such as the masonry-key labels.

Larger is always fine: strokes get wider than two beads and wide spots get extra beads or infill.
Smaller never is: strokes drop under two beads. The browser site has a calculator (`site/`).

Fusion measured 2026-09-23: a Fusion sketch text "H" set at Height 10 mm in Arial and Consolas is
exactly 10.000 mm tall, so Height is the cap height; Beadjoint's cap height (OS/2 sCapHeight) is 700
units = 14 w.

## Fonts

| File | Use |
|---|---|
| `fonts/Beadjoint-Regular.ttf` | fully proportional, kerned: **best for labels** |
| `fonts/BeadjointTab-Regular.ttf` | tabular figures on 9 w cells, for numbers stacked in a column (the footed 1 leaves gaps in 11, 14, 17 on one line); U+2007 figure space aligns them |
| `fonts/BeadjointMono-Regular.ttf` | monospace, 12 w cells (narrow forms of æ œ Æ Œ ø Ø « » — Ĳ Ω; the 14 glyphs still wider than 10 w, © ® ™ ‰ the fractions and ŉ, are left out) |

Side bearings are never under 1 w, so even a program that ignores kerning keeps every pair of glyphs
2 w apart. Kerning (GPOS, plus a legacy `kern` table for the ASCII pairs) tucks overhangs in pair by
pair and keeps accents 2 w clear of their neighbours.

## Rules

- No ink narrower than 2 w anywhere.
- No enclosed hole narrower than 2 w; separate pieces (dots, accents) at least 2 w apart.
- Negative-space pinches narrower than 2 w are filled; inside and outside corners are rounded R0.5 w.
- Wider spots (crossings, filled joints) are allowed: they print with extra beads or infill.
- In a set line every glyph is at least 2 w (1.98 after font rounding) from the next three.

## Slicer profile

The font assumes Arachne walls with the minimum bead width low enough that thick joints step up to
a third bead instead of leaving a void. For the 0.3 mm nozzle declared as 0.4 (w = 0.32 mm), the
tested text profile is `F:/code/masonry-keys/profiles-03as04-arachne` (`profiles_arachne.py`):
`wall_generator = arachne`, `min_bead_width = 50%`, `initial_layer_min_bead_width = 50%`,
`wall_transition_angle = 45`, transition length and filter deviation scaled to the real nozzle.
On other nozzles keep the minimum bead width near 0.6 w and the transition angle at 45.

## Verification

- `cadpy build.py`: the spec's checks (reference results reproduce: P max 2.83 w at the f and t
  crossings, all others at most 2.76), font read-back, set lines from the TTFs.
- `cadpy demo/demo_plate.py` then `cadpy demo/demo_check.py --tag full --crops demo/glyphs`: every
  glyph sliced at native size on a coupon, both faces, with coverage, voids, bleed and single-bead
  detection per glyph, and a bead-level render of each.
- `review/LOG.md`: the design log, one entry per Frodo review round.

## Site

`cadpy site/build_site.py` builds `site/dist`; `cadpy site/serve.py` serves it on port 8765 (LAN).
