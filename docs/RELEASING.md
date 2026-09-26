# Releasing Fillaprint

The end-to-end procedure for cutting a new Fillaprint release, from version bump to the
public website reflecting it. See [DEVELOPMENT.md](DEVELOPMENT.md) for build/test details
and the version-numbering rule (release version -> internal OpenType revision).

## 1. Bump the version

Edit `beadjoint/release.py`:

- `VERSION` — the internal OpenType revision (e.g. `"0.102"`).
- `RELEASE` — the public release tag (e.g. `"0.1.2 beta"`).
- `BUILD_DATE` — an ISO 8601 UTC timestamp for this build, e.g. the date of the release
  commit. This becomes every font's `head.created`/`head.modified` (unless
  `SOURCE_DATE_EPOCH` is set in the build environment, which overrides it).

Nothing else needs to change: `beadjoint/fontfile.py`, `tools/package_release.py`, and
`tools/showcase.py` all read `VERSION`/`RELEASE`/`BUILD_DATE` from this one file.

## 2. Update the change history

- **CHANGELOG.md**: rename the top `## Unreleased — v<old release> (OpenType <old version>)`
  heading to `## v<RELEASE> (OpenType <VERSION>)` (drop the "Unreleased — " prefix; that
  marks the in-progress section that becomes this release). Add a fresh
  `## Unreleased — ...` section above it only once new changes start landing for the next
  release. `tests/test_release.py` parses the topmost `## ` heading against
  `beadjoint.release.RELEASE`/`VERSION`, so the heading must match that pattern exactly.
- **RELEASE_NOTES.md**: replace its contents with the notes for *this* release only (it is
  not cumulative like CHANGELOG.md — its text is pasted directly into the GitHub release
  body). Keep the `Internal OpenType version: **<VERSION>**` line, and the
  `Download **<ZIP_STEM>.zip**` line, in that format: both are conventions readers and
  tooling rely on.
  `tests/test_release.py`'s `ReleaseNotes` check fails on purpose (message: "rewrite
  RELEASE_NOTES.md for the current release — see docs/RELEASING.md") until this line and
  the download name here match the just-bumped `VERSION`/`ZIP_STEM` — that failure *is* this
  checklist step; do not silence it by loosening the check.

## 3. Rebuild the fonts in a fresh pinned environment

```sh
python -m venv .venv && . .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.txt
python build.py
python -m unittest discover -s tests
```

`build.py` exits non-zero if any geometry, outline, or spacing check fails. Confirm the
rebuild actually changed the fonts (or intentionally didn't):

```sh
git status --short fonts/
```

Commit the rebuilt TTFs together with the `beadjoint/release.py` bump and the CHANGELOG /
RELEASE_NOTES updates, in one commit — a font binary and the version it claims to be must
never be split across commits.

Read [DEVELOPMENT.md](DEVELOPMENT.md)'s reproducibility notes first: matching hashes across
machines is not guaranteed even with pinned dependencies and fixed timestamps (GPOS table
packing has varied by a small number of bytes depending on whether `uharfbuzz` is
installed). Compare outlines, metrics, and kerning behavior, not just file hashes, before
deciding a rebuild doesn't match.

## 4. Package the release archive

```sh
python tools/package_release.py --out dist/
```

This reads only `beadjoint/release.py` (no fontTools/numpy/shapely needed) and writes
`dist/<ZIP_STEM>.zip` — e.g. `dist/Fillaprint-0.1.2-beta.zip` — containing the three
committed TTFs, `OFL.txt`, and a generated `INSTALL.txt`, stored uncompressed with fixed
metadata so the archive is byte-identical regardless of which Python/OS built it. It prints
`<path> <sha256>`; record that hash in the release notes or commit message if you want it
pinned somewhere reviewable.

Run it twice into different output directories and diff the results if you want to confirm
reproducibility locally before tagging:

```sh
python tools/package_release.py --out /tmp/rel-a
python tools/package_release.py --out /tmp/rel-b
diff <(sha256sum /tmp/rel-a/*.zip | cut -d' ' -f1) <(sha256sum /tmp/rel-b/*.zip | cut -d' ' -f1)
```

## 5. Tag and publish the GitHub release

```sh
git tag v<RELEASE without the " beta">-beta          # e.g. v0.1.2-beta
git push origin v<RELEASE without the " beta">-beta
gh release create v<tag> dist/<ZIP_STEM>.zip fonts/*.ttf OFL.txt \
    --title "Fillaprint v<RELEASE>" --notes-file RELEASE_NOTES.md
```

Releases are immutable: never move or re-push an existing release tag, and never overwrite
a published release's binaries. A mistake ships as a new release, not a silent edit.

## 6. Update the website

The website repo builds its own copy of the public assets from a pinned commit of this
repo (see its `scripts/sync-fillaprint.py`, which records the source revision it last
synced from). After pushing the release commit and tag here:

1. In the website repo, update the pinned source revision to this release's commit.
2. Re-run its sync script against this checkout.
3. Confirm the site's coverage/provenance JSON and character specimen reflect the new
   `VERSION`, and that its font bundle matches `tools/package_release.py`'s output for this
   revision (same member list, same `INSTALL.txt` wording driven by `RELEASE`/`VERSION`).
4. Commit and deploy the website separately; it is a different repository with its own
   review process.

## Checklist

- [ ] `beadjoint/release.py`: VERSION, RELEASE, BUILD_DATE bumped together
- [ ] CHANGELOG.md: top heading renamed to the shipping release
- [ ] RELEASE_NOTES.md: rewritten for this release only (`tests/test_release.py`'s
      `ReleaseNotes` check passes — it fails on purpose until this is done)
- [ ] Fresh pinned rebuild: `build.py` and `python -m unittest discover -s tests` pass, with
      zero failures (not even the expected `ReleaseNotes` one — see the line above)
- [ ] `git status --short fonts/` reviewed (empty, or the diff is expected and explained)
- [ ] Fonts + release.py + CHANGELOG/RELEASE_NOTES committed together
- [ ] `tools/package_release.py --out dist/` run; hash recorded
- [ ] Tag pushed, GitHub release published with the archive and individual TTFs attached
- [ ] Website re-synced at the new revision
