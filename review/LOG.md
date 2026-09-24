# Beadjoint design log

## Round 0 — from the spec to a full character set (2026-09-23)
- Built the spec's sets P (proportional), M (monospace) and the tabular 1; the spec's reference results reproduce: P max 2.83 w at the f and t crossings, everything else at most 2.76, M max 2.83, no thin pieces.
- Extended to 350 glyphs: A-Z, all ASCII symbols, Latin-1, Latin Extended-A, Romanian comma-below letters, dashes, quotes, primes, euro, trade mark, fractions and superscripts (small figures: the figure outlines with their 4 w counters squeezed to 2 w).
- Accents sit 2 w clear of their letter: bottom at y = -2 over x-height letters and y = -6 over capitals and ascenders; cedilla and ogonek attach to the bottom stroke; Latvian and Romanian letters use a comma below; the caron on d, l, t, L is an apostrophe.
- User rules (2026-09-23): thin ink is forbidden; thin enclosed holes are forbidden; thin open negative space is tolerated but pinches are filled; infill in wide spots is fine. Every glyph is finished by filling negative-space pinches narrower than 2 w, rounding inside corners R0.5 and outside corners R0.5.
- N: a 7 w N with a diagonal makes 3-3.5 w blobs and whole-counter pinches, so it became a 9 w zigzag. The user found it "going to fall over"; under review.
- ø: at x-height a slash through the 6 w counter leaves pinched islands, so the slash passes behind the o (stubs outside the ring). Ø keeps a 40 degree through-slash (its counter is tall enough).
- & redrawn as a small top loop, open lower bowl and straight tail; K joins its arms to the stem with a short bar; © and ® sit in a 14-16 w ring (the inner letter needs 2 w all round).
- Demo slice of every glyph on both faces: crossings and filled joints left small voids on the top surface because only_one_wall_top limits the top layer to one loop (two beads); re-slicing with it off for the text profile.

## Round 1 — Frodo on letters and on symbols/spacing
- N, M, W as one system: N has full stems and a diagonal whose edges land on the outer corners (flat ends on all four corners, symmetric under 180°, stands upright); M has full stems and a V meeting at (5, 5) with a constant-width r = 2 hairpin; W is M turned over. The zigzag N "fell over", the squared M read as m, the squared W as Ш.
- S no longer a 5: r = 2 corners and a slanted spine. G no longer a 6: hooked top ending in a ball, bar stops at x = 4. C rounded to match. R gets a straight ball-ended leg (was an A with a kink). ß ends its lower bowl in a free ball (read as B). K's arms meet the stem like k (the bar made a 4.7 w blob).
- ľ Ľ ď ť: the apostrophe slides in until it is 2.05 w from the letter, top cut flat on the cap line. ŀ's dot moved to mid x-height.
- Small figures: the small 1 has the tabular 1's foot (¼ ½ ¹ read as 7/4 7/2 and a superscript 7). The proportional 1 uses the footed 1 as well.
- Quotes and comma have a head: ’ = ball head with a tail, ‘ its mirror (they were identical), , and ; and „ from the same head. Asterisk: five ball-ended spokes (the raised x read as x). ° is a round 7 w ring with a 3 w hole (it read as a dot). • is 4 w (it matched ·). % and ‰ dots are 3.5 w (the lower one looked like a period). § is full height with a 3 x 4 centre loop (read as 5). ¬ sits on the math axis; ¤ recentred.
- Setting: glyphs that share almost no scanline keep their ink boxes 1 w apart (the hyphen hid under the inch mark in 1/2"-5/8", ' over . read as !); punctuation tucks at most 1 w; ink boxes overlap by at most (narrower width - 2 w)/2 so in any A B C the outer two stay 2 w apart ("4.48" printed as "48"). The line check now covers each glyph against the next three, not just its neighbour.
- Word space: edges halfway between the ink inside y in [-4, 10] and the bbox (a j hook counts half), measured from the whole previous word, with a 3.5 w true-distance floor; a figure run after a space starts at its first figure's edge, not its cell. The fonts carry the half-band edges in their space kerns.
- Slicer profile (text): Arachne min bead width 50 % and wall transition angle 30 deg cut demo-slice voids at crossings and filled joints from 3.9 to 0.8 mm² (14 worst glyphs); classic walls were 12.3.
- Fonts: side bearings never below 1 w, so even without kerning no two glyphs come closer than 2 w; accented letters share their base's kerning class; 6.7k exception pairs keep marks 2 w clear; the gap floor is 2.02 w so the TTFs (outlines on a 1/50 w grid) pass the 1.98 check. Win metrics now cover the tallest accent and the lowest comma.

## Round 2 — Frodo on accented letters (165 composites, 29 specials)
- ģ was broken: U+0123 decomposes with a cedilla, and the comma-below fused into the g's tail (a g with a long tail). It now takes the turned comma above, 2 w clear.
- Default line pitch 28 w (was 20 w): at 20 w, g over ( already collides, p over Á needs 26.4 w and g over Å 28 w. The fonts' line gap carries it; 20 w stays fine for unaccented labels like the masonry keys.
- ħ and đ: the stem now pokes 2 w above the bar (ħ read as Cyrillic ћ, đ as a d with a hat).
- Mono: ĺ was forced over x = 1 and came out too wide, so Mono silently dropped it; Mono now anchors the acute on its own l stem, and ď ť in Mono get a centred caron (the apostrophe form does not fit a 12 w cell).
- Breve is a half circle (the square cup read as a small u); the ring is a true circle with a 2 w hole; ŗ's comma sits under the stem, not under the arch.
- Checked and kept: acute/grave slope (47°, the best separation), mark heights, ð in the ∂ form, ĸ, ł Ł, the ø stubs, ogonek vs cedilla vs comma-below, Ţ with a comma, every round-1 decision.

## Round 3 — Frodo on how it prints (all 350 glyphs sliced, both faces)
- Two beads everywhere: no single wide bead on any of 700 glyph faces; dots print solid; small marks print clean.
- Inside fillets only where they seal a notch, slit or pinhole: the R0.5 fillet in every open corner swelled crossings from 2.83 to 3.22 w and T-joins from 2.5 to 2.75 w, and the one-wall top layer printed that as 0.52 mm beads pushing colour 0.1 mm past the outline. Beads over 0.48 mm went from 26 to 0.
- Text profile wall_transition_angle 45 (was 30), together with the fillet change: visible specks (voids on both colour layers) fell to at most 0.013 mm²; v, N, V, K and & went to 0. 45 without the fillet change opened voids under # and f.
- The demo checker now scores visible specks (voids at least 0.05 mm wide on both colour layers) instead of hairline seams where a loop's two beads meet.

## Round 4 — Frodo on real labels, spacing and kerning
- The TTFs match the setting engine within 0.11 w on every pair of 63 labels; word spaces within 0.04 w on all 8,836 ASCII pairs.
- Beadjoint (proportional) is the label font; Beadjoint Tab is for numbers stacked in a column (its footed 1 leaves 3-4.3 w holes in 11, 14, 17 on one line). Tab gains U+2007 figure space.
- The engine counts repeated spaces like the fonts do; no-break and thin spaces, U+2010/2011 hyphens, μ and ⌀ map to existing glyphs (engine and cmap); a missing character raises one clear error naming all of them.
- To verify: whether Fusion applies kerning ("TjTjTjTj" at Height 4.48 mm: 16.0 mm kerned, 20.0 mm not). If not, make key text through the font reader and import outlines.
- Kept: word space 5.5 w, tracking (the 2.02 w floor sets it; change only on print evidence).

## Round 6 — Frodo on Beadjoint Mono
- Capital W was missing from Mono: rotate180 left it 10.0004 w wide against a 10 w cut-off with 1e-6 slack (tolerance now 1e-3).
- Mono setting now maps aliases and names missing characters like the other settings.
- Mono 0 is 8 w with r = 1 corners (the spec's widened 0 was the same 9 w rounded box as O, so serial numbers blurred 0 and O).
- Ø ø stay out of Mono (their slash needs more than a 12 w cell).

## Round 5 — Frodo on figures, units and new symbols
- New: Ω (also the Ohm sign U+2126), ⅛ ⅜ ⅝ ⅞ (small figures like ¼ ½ ¾), ← ↑ → ↓, ≤ ≥ ≈. Ω needed a 6 w inner width and flared feet (10 w span) before it stopped reading as a cursive u.
- Checked and kept: figures, superscripts, ¼ ½ ¾, ° ± × µ % #, and the colon in 12:30.

## Round 7 — Frodo on legibility at print size (blurred, ink grown 0.3 w)
- Ω: the round-5 flared feet washed out at print size and it read as n or ∩; the legs now splay out from mid height (15 w wide, so Ω is not in Mono).
- Open: in runs like "vvw" every notch blurs to the same depth; w's own notch cannot be closed further without a structural change. Left as is (rare in labels).
- Open: º is a raised full-size o (an ordinal needs a smaller o, which cannot keep a 2 w counter).
- Follow-up: pairs of V-shaped letters (v w y V W Y and their accented forms) get 0.6 w extra, so "vvw" no longer blurs into one run of equal notches.

## Round 8 — Frodo on the masonry-key labels (sliced both faces)
- Recommendation: set the key labels at 1.2× (cap height 5.4 mm): all nine keys fit, beads only get wider. The tightest is 5/16" (2 mm total spare); print it once before locking the set in.
- Toolpaths on both faces: no specks, voids or lost detail in fractions, inch marks or periods; two-line centring exact.
- The fraction hyphen (1-1/8") and the range dash (" - ") are the same glyph, told apart only by spacing; an en dash (–) for ranges in the Fusion labels would make them distinct shapes.

## Round 9 — Frodo on the site
- The files list recommended Beadjoint Tab for labels; it now puts Beadjoint (proportional) first as the label font, Tab for columns. The type tester defaults to the proportional font.
- Added how to install on Windows (right-click the .ttf, Install) and that Fusion must be restarted to see new fonts.
- The size calculator answers "what Height in Fusion" in seconds; the phone layout holds.

## Round 10 — Frodo, final sign-off
- Signed off. Tests 10/10. README's slicer section still said transition angle 30; now 45 as shipped. No other contradictions between the log, README and profile; the review sheets show no remaining problems beyond the two open notes from round 7 (vvw notch blur, raised º).

## Round 11 — the user on Ω (2026-09-24)
- On the symbols sheet the user could not tell what Ω was: the round-7 legs splaying from mid height read as 人 or a lambda. Four redesigns were drawn and checked; the user chose A: the bowl (O's r = 2 corners) pinches in to two legs 2 w apart and turns out into flat feet on the baseline, 11 w wide (was 15). Still too wide for Mono's 10 w, so Mono keeps omitting Ω and the ohm sign.
- Fusion checked after a restart: sketch text Height is the cap height (4.48 mm gives a 4.48 mm H), and Fusion applies the fonts' GPOS kerning ("TjTjTjTj" 16.04 mm, the file's kerned width; unkerned would be 20.07 mm).
- Fonts v1.101. build.py imported the removed GLYPH_NAMES table; it now names glyphs with charset.glyph_name.

## Round 12 — the user on A and R, Sauron on coverage (2026-09-24)
- A and R read alike at label size (both: left stem, flat top, bar at mid height, something landing bottom right). A's legs now run straight up to the bar and lean in 5 degrees above it, the kink hidden by the bar; still 7 w like the other capitals, the counter's top corners filleted by the finish (the user: narrow negative space there prints fine). The pointed and sloped-leg As were rejected (the pointed apex made a 5.1 w lump). R unchanged.
- Sauron's coverage audit: every common European keyboard layout, cp1250/1252/1257 and ISO-8859-1/2/3/4/9/13/15/16 were covered except Welsh ẁ ẃ ẅ ỳ (with capitals) and the lira sign ₺; both added. At the user's request also ƒ (slanted stem), ẞ (sharp top right, diagonal to a rounded U-turn, tail ball 2 w off the stem so it cannot close into a B), ≠, ⅓ ⅔, and ― as an alias of the em dash.
- The fonts declared no Windows code pages (OS/2 ulCodePageRange 0), so GDI apps could substitute another font for Central European, Turkish or Baltic text; the unicode and code page ranges are now computed from the cmap. The cmap aliases now come from charset.ALIASES (they were a second, hand-kept list).
- Mono gained narrow (10 w) forms of æ œ Æ Œ ø Ø « » — Ĳ Ω, so Danish, Norwegian and French can be set in Mono; ⌀ and the ohm sign follow Ø and Ω. Still left out of Mono: © ® ™ ‰, the fractions and ŉ.
- w (the user: not wild about it): the V-built w read as a u with a bump, and raising its middle fold 0.5-1.5 w did not fix it. It is now a turned m with a short middle stick (top 4 w below the x-height), square like u and m, 10 w wide in all three fonts; its widest point drops from 3.5 w (filled valleys) to 2.5 w. ŵ ẁ ẃ ẅ follow. v and y keep their diagonals.
- Released together with round 11 as v1.101.

## Renamed Double bead (2026-09-24)
- The user chose the name Double bead after a mockup. Fonts v1.200: families Double bead, Double bead Tab and Double bead Mono, files DoubleBead*-Regular.ttf; glyphs, spacing and sizing are v1.101's. The installer removes the Beadjoint-named installs. The code package, repository and this log keep the working name.
