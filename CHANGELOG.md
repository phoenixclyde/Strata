# Changelog

All notable changes to this project (the gfx906/MI50 port line of Strata) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org) for the upstream
version axis (`0.2.x`), with a port-drop suffix (`rN`) for this fork's release series
(`mi50-0.2.x-rN` tags).

Upstream releases (Niko1221/Strata) keep their own user-facing notes in
`docs/release-notes-*.md`; this changelog records the changes of this port line.
Earlier port drops before this file existed are documented by their annotated tags
(`mi50-*`): `git tag -l 'mi50-*'`.

## [Unreleased]

### Added

- `THIRD-PARTY-NOTICES.md`: aggregated third-party licence inventory (6 vendored
  components x licence x copyright x pin), and full-text `LICENSE` files for
  `third_party/ggml-tq/` and `third_party/libstrix/` (Google OSS requirement:
  every vendored subdirectory carries the licence text itself, not a link).
- `CHANGELOG.md` (this file) and `docs/RELEASE_RECEIPT.md`: the release receipt
  template (upstream ref / local ref / gate results + naming boundary note).
- `ci/LEDGER_FORMATS.md`: single source of truth for `CI_RUNS` /
  `SOURCE_PROVENANCE` / `REBUILD_RECIPE` formats and D7 thresholds.
- Governance repository initialisation (workspace git + `.gitignore`) and
  `docs/audits/2026-11-10-m7-freeze/` frozen evidence archive (58-entry sha256
  manifest; frozen ledgers never overwritten by live ones).
- `deploy/REPLY_COPIES_INDEX.tsv`: index of the 34 `_bak` reply copies (P14/U19).

### Changed

- `ci/deploy_gate.py`: D1-D7 merged into a single implementation (was two
  divergent copies); `reg_allowed` now fail-closed on a missing/overridden
  register path (bad path = empty allow-list = REFUSE, no traceback); self-test
  15/15 on both hosts.
- `ci/gpu-gate.yml` migrated to the default branch (SHA-pinned checkout; the
  broken GDN_PP step removed and tracked as a CAR item).
- `ci/build.sh` / `ci/deploy.sh`: refuse to build/deploy from a non-mainline ref
  unless `--allow-non-mainline` is given (and logged).
- `albus/w1003/mirror_check.py`: mirror target set derived from
  `git ls-files deploy/` (was a hand-picked 7-file list); incremental `--sync`;
  byte-safe remote batching (the 8191 argv truncation trap).

### Security

- `.gitignore` keeps credentials (`_tok.txt` and friends) out of the governance
  repository; token rotation remains a manual owner step (G13).
- Branch protections (no force-push, no delete) on `ci/*`, `main`, `bench-*`
  during the convergence window.

<!-- Release sections (## [mi50-0.2.x-rN] - YYYY-MM-DD) are added at release
     time from the Unreleased section above, following docs/RELEASE_RECEIPT.md.
     Older drops: see the annotated mi50-* tags. -->

[Unreleased]: https://github.com/phoenixclyde/Strata/compare/mi50-0.2.11-r33-15...HEAD
