# Printing and sizing

Use the extrusion line width **w** your slicer will actually use for the text.
Nozzle diameter and extrusion width are not necessarily equal.

| Measurement | Formula | w = 0.32 mm | w = 0.42 mm |
| --- | --- | --- | --- |
| Capital height / Fusion text Height | 14 × w | 4.48 mm | 5.88 mm |
| Em-based font size | 20 × w | 6.40 mm | 8.40 mm |
| Font size in points | 20 × w ÷ 0.3528 | 18.1 pt | 23.8 pt |
| Nominal stroke / minimum clear gap | 2 × w | 0.64 mm | 0.84 mm |
| Lowercase x-height | 10 × w | 3.20 mm | 4.20 mm |
| Default baseline-to-baseline pitch | 28 × w | 8.96 mm | 11.76 mm |
| Pitch for comma-below letters over tall accents | 30.6 × w | 9.79 mm | 12.85 mm |

Fusion's text Height was checked against actual capital outlines on 2026-09-23.
Other applications can interpret text size differently: measure an outlined **H**
if uncertain. The fonts use 1000 units per em and a 700-unit capital height.

At the reference size, nominal strokes are two line widths wide. Joins and
crossings can be thicker. Enlarging the font preserves its proportions but can
add toolpaths; shrinking it below the reference size removes the two-bead margin.
Always inspect your own sliced preview, particularly for counters and accents.

The 28 w line pitch keeps ink on neighbouring lines at least 2 w apart for every
character but one group. Ink reaches 22 w above the baseline (the ring of Å) and
4 w below it (descenders): 22 + 4 + 2 = 28.

The exception is the comma-below letters Ģ Ķ ķ Ļ ļ Ņ ņ Ŗ ŗ Ţ ţ Ș ș Ț ț, used in
Romanian and Latvian. Their commas reach 6.6 w below the baseline. Above a letter
with a tall accent on the next line, the gap can fall below 2 w: capitals with a
ring, breve, grave, acute, double acute, circumflex, caron or tilde (Å Ů Ă Á Â Š Ñ
and others), and ĥ ĺ (in Mono also ď ť). At the closest horizontal position, ș
touches Å. For text that can stack these, set the baselines 30.6 × w apart
(22 + 6.6 + 2), about 1.1 times the default pitch or 1.53 times the em.

Reducing the pitch to 20 w is only appropriate for selected unaccented label
combinations after checking the actual lines. Do not assume it is safe for
arbitrary multilingual text.

## Recorded slicer setup

The committed toolpath showcase comes from OrcaSlicer's Arachne wall generator,
using w = 0.32 mm on the top face of a demo coupon. The author's test used a real
0.3 mm nozzle with a 0.4 mm nozzle setting in the slicer. This is a record of that
experiment, not a general instruction to misstate your nozzle diameter.

| Setting | Recorded value |
| --- | --- |
| `wall_generator` | `arachne` |
| `min_bead_width` | `50%` |
| `initial_layer_min_bead_width` | `50%` |
| `wall_transition_angle` | `45` |

The profile allowed thicker joins to receive an extra bead. Transition length
and filter deviation were adjusted for the real nozzle. Different slicers,
profiles, orientation, extrusion calibration, and materials can change results.
The showcase is toolpath evidence for that setup, not a guarantee for every print.
