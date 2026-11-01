# ci/ — the downstream gate and the deploy loop

This directory holds the part of our CI that must run **in two places**: on a GitHub runner
(no GPU, seconds) and on the 166 host (has the GPU, the build tree and production).

## What runs where

| Where | What | Entry |
|---|---|---|
| GitHub runner | `ci/gate.py --source-only` — config-face checks on `src/`, `include/`, `CMakeLists.txt` | `.github/workflows/downstream-gate.yml` |
| GitHub runner | upstream gap check, opens/updates an issue | `.github/workflows/upstream-watch.yml` |
| GitHub runner | upstream's own server + monitor suites (untouched) | `terminal-minimal-server.yml`, `terminal-portable-monitor.yml` |
| 166 host | the same gate, plus build tree and live config | `/home/albus/strata166/ci/strata-ci check` |
| 166 host | build one TU, install, restart, verify, ledger | `strata-ci build` / `deploy` / `rollback` |

The other scripts (`config.sh`, `build.sh`, `deploy.sh`, `rollback.sh`, `strata-ci`) live
only on 166: they hardcode production paths and must never be run from a laptop.

## The loop

```bash
ci/strata-ci check                  # seconds, no GPU, no restart; exits 1 on any FAIL
ci/strata-ci build                  # one TU, verbatim ninja commands, ~8-10 min
ci/strata-ci deploy                 # DRY RUN: prints every step and changes nothing
ci/strata-ci deploy --apply         # tag-gated; writes a ledger line afterwards
ci/strata-ci rollback --last        # back to the previous engine, no rebuild
ci/strata-ci status                 # engine / health / binary / git / ledger
ci/strata-ci watch                  # is upstream ahead?
```

`deploy` refuses to run unless `HEAD` carries a `mi50-*` tag. That is the rule
"生产只跑发布 tag 对应的 HEAD", enforced by the tool instead of by memory.

## What the gate checks, and why each one exists

Every check below corresponds to a mistake that actually happened or was measured here:

| Check | The mistake it prevents |
|---|---|
| `wave_rows_for()` exists | the R table silently dropping out of a rebuild |
| `STRATA_MMVQ_WAVE_ROWS` has a real `getenv()` | the rollback switch that existed **only in a comment** |
| no hardcoded `R>1` in the function | one shape's tuning leaking to every shape |
| every `kWaveRows` cell is `0` or in `{1,2,4}` | a typo turning into an unmeasured kernel |
| `ncols=1` stays at `R=1` | re-introducing the row count we measured as a 10% loss |
| trailing `return 1;` | an unmeasured shape picking an unmeasured kernel |
| `-DNDEBUG` present | a 47% slowdown (measured) |
| `include/strata/platform/hip_compat` | a 45% slowdown (measured) |
| no `.bak/.orig` under `src/` | backups polluting the tree and the diff |
| `docs/DOWNSTREAM.md` anchored | a rebase with nothing to check the patch stack against |
| live `exe` exists, env is `0/1/unset` | a config pointing at a binary that is not there |

## What this gate cannot do

It checks the **config face**, not numbers. A kernel that compiles, keeps every switch and
still computes the wrong thing passes here. That is what the on-host bit-exactness run and
the A/B measurement are for — they need the GPU, so they stay in `deploy`'s manual path.
