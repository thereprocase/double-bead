# Changelog

## Unreleased — v0.1.1 beta (OpenType 0.101)

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

- `demo/slicer_support.py`, starter OrcaSlicer presets in `demo/profiles/`, and repo-relative
  paths throughout `demo/` and `review/`: slice validation runs from a fresh clone.
- `tests/test_slicer_support.py`.
- Byte-reproducible builds: fixed font timestamps (`BUILD_DATE`, or `SOURCE_DATE_EPOCH`).
- Reproducible-build instructions in `docs/DEVELOPMENT.md`; dot rationale and tuning in
  `docs/SPEC.md` §11a.

## v0.1.0 beta (OpenType 0.100)

First release under the Fillaprint name. See `RELEASE_NOTES.md`.
