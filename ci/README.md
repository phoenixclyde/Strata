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

## W1002 — the round gate (why the previous "mechanism" was not one)

Before W1002 the only caller of any gate was `pre-commit -> gate.py --source-only`.
`report_lint.py` lived on the laptop, the repack A/B sources lived in `/tmp` and
`build-tab/repacktest/`, `PORT_STATUS.md` did not exist, and 16 commits sat unpushed.
Nothing checked any of that. **A tool without a caller is not a gate.**

| Trigger | Gate | What it refuses |
|---|---|---|
| `git commit` | `pre-commit` → `gate.py --source-only` + `round_gate.py --ci` | broken config face; missing/stale A/B evidence; a `report_lint` that no longer rejects a broken report |
| `git push` | `pre-push` → fork policy + `round_gate.py --ci` | pushing to upstream; publishing a state with missing evidence |
| push on GitHub | `downstream-gate.yml` → `verify.py` + `round_gate.py --ci` | same checks, independently, on a clean runner |
| round closing (166) | `round_gate.py --status` | unpushed commits, dirty tree, hooks not installed |
| round closing (laptop) | `albus/w1002/round_close.py` | `report_lint` FAIL, `plan_lint` FAIL, missing four-section report, authoritative plan drifted from the 166 mirror |

**A tool pointed at the wrong copy is not a gate either (W1003).** `plan_lint` reads the laptop's
`deploy/W832_OPT_PLAN_V2.md`. The 166 copy of that same file had not changed since 2026-11-03 02:54 —
18 rounds (W882-W1002) of write-backs existed only on the laptop, and nothing compared the two, so the
gate stayed green against a file nobody on the box was reading. `albus/w1003/mirror_check.py` now
compares both files byte for byte over ssh; `round_close.py` treats a mismatch as a hard failure and
`--sync` pushes the laptop copy (now the primary) leaving a dated `.bak` on 166. The comparator has its
own negative self-test: a forged all-zero remote hash must be reported as DRIFT.

Negative self-tests are mandatory: `round_gate.py --ci` runs `report_lint` against
both a complete four-section report (**must PASS**) and a conclusion-only text
(**must FAIL**). A lint that always passes is worse than no lint.

Local-only scripts (they hardcode Windows paths) stay on the laptop:
`report_lint.py`, `ledger_lint.py`, `param_pair_lint.py`, `plan_lint.py`,
`round_close.py`. The repo copy `ci/report_lint.py` is kept byte-identical to
`tools/report_lint.py`; `verify.py` checks it exists.
