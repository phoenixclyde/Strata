# Release receipt template (B5)

Every release of this port line (a `mi50-0.2.x-rN` tag and its GitHub Release)
carries a receipt at the top of its release notes. The receipt has exactly three
data lines plus one naming-boundary note. Copy this block into the release notes
and fill it in; do not delete lines you cannot fill — write `MISSING` instead, so
the gap is visible.

## Receipt block (copy into the release notes)

```
Receipt
- upstream ref: <upstream commit or tag this release is based on, e.g. v0.2.12 @ 146df3c46>
- local ref:    <this release's tag and commit, e.g. mi50-0.2.12-r34 @ <sha>>
- gate results: <verification gates run for this release and their verdicts,
                e.g. "build OK (b12180, md5 ...) / A/B 2xCV PASS / deploy_gate D1-D7 PASS
                / gh run #NNN success" — one line, semicolon-separated>

Strata is an open-source project by Niko1221 and the Strata contributors (MIT).
This repository is a community gfx906/MI50 port; it is not an official Strata
release and is not affiliated with or endorsed by the upstream project.
```

## Field rules

| Field | Must contain | Notes |
| --- | --- | --- |
| `upstream ref` | The upstream (Niko1221/Strata) tag **and** commit sha the release is rebased onto | If the fork has drifted, state both the last rebase point and the drift count (`ahead N`) |
| `local ref` | The `mi50-*` tag name and its commit sha | Tag must be annotated (`git tag -a`), message follows the "MI50 drop rN: ..." convention |
| `gate results` | Every verification gate actually run, with verdict | Minimum for a production drop: build + A/B (2x CV) + deploy_gate; `MISSING` for anything not run — never silently omit |

## Naming boundary (the one sentence)

The last paragraph of the receipt block is the naming-boundary note. It is
mandatory in every release and must stay a single factual sentence pair:
nominative use only ("a community gfx906/MI50 port"), never "official",
"certified" or any wording that implies endorsement. Do not translate it away;
keep it in English so it reads the same in every release.

## Publishing (P10: GitHub Releases from tags)

1. Tag: `git tag -a mi50-<ver>-r<N> <sha> -m "MI50 drop rN: <one-line summary>"`.
2. Push the tag: `git push origin mi50-<ver>-r<N>`.
3. Create the GitHub Release **from that tag** (`gh release create mi50-<ver>-r<N> --notes-file <notes>`),
   not from a branch. The release notes file starts with the receipt block above,
   then the user-facing sections in the style of `docs/release-notes-*.md`.
4. The CHANGELOG entry for the version is cut from `## [Unreleased]` in the same
   commit that tags the release (Keep a Changelog: move Unreleased items into
   `## [mi50-<ver>-r<N>] - <date>`).

The three receipt lines make a release auditable after the fact: which upstream
it sat on, which local commit shipped, and which gates actually ran. A release
without a receipt is not a release of this port line.
