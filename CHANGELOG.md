# Changelog

<!-- Each release heading is "## [Unreleased — ]v<RELEASE> (OpenType <VERSION>)", matching
     beadjoint/release.py's RELEASE and VERSION; tests/test_release.py parses the topmost one.
     Rename "Unreleased" to the tagged release once it ships; never renumber a shipped entry. -->

## v0.1.3 beta (OpenType 0.103)

### Changed

- **V** is 1w wider: the round point now joins arms whose centres are 8w apart (was 7w),
  giving 10w of ink, as wide as M and W and still inside the Mono cell. The wider angle
  lowers its joint fill from 2.17 to 1.82 w².
- **Z**'s top and bottom bars are longer. The mitred corners stuck out about 0.6w past the
  free bar ends, so the bars read short; each bar now runs 0.5w past the opposite corner tip
  (1.1w longer, Z 1w wider). The diagonal and corners are unchanged.
- Both were chosen in review from four candidates each (see the Fillaprint page's capital
  V / Z candidates section). Spacing and kerning around V and Z changed, so text containing
  them can reflow. Fillaprint Mono uses the same V and Z.

## v0.1.2 beta (OpenType 0.102)

### Changed

- **v** and **z** are sharper, with less solid fill in their joints (chosen from five
  candidates each in review; see the Fillaprint page's v / z candidates section).
  v's arms now meet in a plain round join (the stroke's own 1w radius, was a 2w curve) at an
  8.5w spread (was 7w): joint fill 2.17 → 1.06 w². z's diagonal is steeper (61°, was 55°)
  with mitred corners: joint fill 1.57 → 0.33 w². v is 1.5w wider; spacing and kerning
  around v and z changed, so text containing them can reflow.
- **V** and **Z** follow: V has the same round point at a 7w spread (9w ink, like N and O;
  joint fill 4.12 → 2.17 w²); Z keeps its 65° diagonal with mitred corners.
- **Fillaprint Mono** v and z use the proportional shapes (both fit the 12w cell). A wider
  Mono z would flatten the diagonal and refill its notches.
- M and W are unchanged: a round point in their narrow, cap-cut V would triple its fill.

### Tests

- `SpecReference.test_set_p` allows the spec-set lowercase up to 2.81w (v's round join
  measures 2.80w; the R2 limit is 2.85w). The tuner's radius-range test uses S's corner.

## v0.1.1 beta (OpenType 0.101)

### Fixed

- **ĳ** no longer prints as one solid 5.5w slab. After the dots grew to 3w, the i and j
  of ĳ sat 1.5w apart and finishing filled the gap. j now sits 2.5w further right: ĳ is
  8w wide with 2w gaps, like a typed "ij". Advance 425 → 500 units; its kerning changed.
- **Fillaprint Mono**: `.notdef` takes the full 600-unit cell (it was 500 units wide and
  broke the grid for the 14 characters Mono leaves out); J " - . / use the same shapes as
  the other families; OS/2 PANOSE marks the family monospaced.
- `.notdef` has 2w walls in all three families (8w × 14w box with a 4w × 10w counter).
- Left side bearings in `hmtx` equal each outline's leftmost point (Mono `]` was one unit
  off, which shifts it in renderers that position glyphs from `hmtx`).
- Construction: a rounded corner whose neighbours lie on a straight line no longer divides
  by zero, and a stroke point that coincides with its neighbour raises a named error.

### Changed

- `build.py` now fails on the rules `docs/SPEC.md` §11 lists: spec-set strokes over 2.85w,
  pieces closer than 1.98w, pieces joined by finishing (Mono k's designed join excepted),
  and shipped glyphs thicker than 4.85w. Thickness maxima remain reported.

### Documented

- **Line spacing**: at the default 28w pitch, letters with a comma below (ș ț ķ ļ ņ ģ ŗ …)
  stacked directly under accented capitals (Å Ă Š …) come closer than 2w. Such labels need
  30.6w (1.53 em). README and `docs/PRINTING.md` give the details.
- `docs/SPEC.md`: the finishing the fonts apply (pinch fill, inside fillets, soft corners),
  the real cell gaps and the Tab digit budget, `.notdef` and side-bearing rules.


### Changed

- **Dots are 3w across instead of 2w** (spec rule R11, `DOT` in `beadjoint/geom.py`):
  i, j, `.` `:` `;` `!` `¡` `?` `·` `÷` `…`, ŀ Ŀ, and the dot and dieresis marks
  (ė ż ä ö ü ï and the other precomposed letters that use them).
  - Visual: a stem-width disk looks lighter than the stem; the larger dot matches its weight.
  - Print: a 2w dot slices as one loop around a point and is often lost; a 3w dot gets a loop
    around a solid core.
  - Each dot keeps its edge on its guide line and stays 2w clear of its stroke, so i and j
    now reach 1w above the ascender line; `.` `:` `!` `¡` are 1w wider and `…` 3w wider.
  - Fillaprint Mono keeps 2w dots in `…` only: three 3w dots do not fit its 10w cell.
  - `%`, `‰` and `•` are unchanged (their dots were already 3.5w and 4w).
- Advance widths and kerning of the affected glyphs changed. Text set in v0.1.0 can reflow.

### Added

- **Glyph tuner** (`python -m tuner.serve`, see `docs/TUNER.md`): a local tool that edits
  the numeric coordinates and radii of existing glyph constructions, previews the real
  geometry, validates every changed glyph in all three families (including gaps that
  finishing would fill), and exports an ordinary Git patch. The 297 superseded review
  screenshots were removed from the working tree; they remain in Git history.
- Release tooling: `beadjoint/release.py` holds the version, `tools/package_release.py`
  builds a byte-reproducible release archive, `docs/RELEASING.md` describes a release, and
  CI runs the tests on Linux, macOS and Windows and checks that a pinned rebuild
  reproduces the committed fonts.
- `demo/slicer_support.py`, starter OrcaSlicer presets in `demo/profiles/`, and repo-relative
  paths throughout `demo/` and `review/`: slice validation runs from a fresh clone.
- `tests/test_slicer_support.py`.
- Byte-reproducible builds: fixed font timestamps (`BUILD_DATE`, or `SOURCE_DATE_EPOCH`).
- Reproducible-build instructions in `docs/DEVELOPMENT.md`; dot rationale and tuning in
  `docs/SPEC.md` §11a.

## v0.1.0 beta (OpenType 0.100)

First release under the Fillaprint name. See `RELEASE_NOTES.md`.
