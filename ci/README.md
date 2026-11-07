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

## Fork 的 Actions 开关（W1029，实测；`gh_gate.py` 就按这四条报错）

`POST /repos/{owner}/{repo}/actions/workflows/{file}/dispatches` 返回
**422 `Actions has been disabled for this repository`**，而
`GET /repos/{owner}/{repo}/actions/permissions` 同时报 `enabled: true, allowed_actions: all`。
两句可以同时为真：前者是**这个 fork 的 workflows 有没有被启用**，后者是**策略允许什么**。

四条要一起做，缺一条都不动：

1. **Settings → Actions → General → Allow all actions and reusable workflows**，然后点这一节的 **Save**。
   只选中不 Save 等于没改。
2. **Actions 标签页**（`https://github.com/<owner>/<repo>/actions`）顶部的横幅
   *"Workflows aren't being run on this forked repository"* → 点
   **"I understand my workflows, go ahead and enable them"**。Settings 里没有替代品。
3. **推一个新提交**。GitHub **不回填**：开关关着时推上去的 sha 永远不会补跑。
   实测 `e4f0867d`（空提交）推到 origin 后 180 s 内无 run。
4. 第 1 步若改不动/自己变回去，是账号或组织策略，去 **Settings → Billing and plans** 看有没有 hold。

判据一条命令：`python3 ci/gh_gate.py --wait 300`（exit 6 = 没 run，并会打印上面四条）。
`ci/deploy.sh` 第 0 步就是它：**开关没开 = 部署被拒**，这是故意的。

## W1046 (2026-11-07): isa_dump.sh, and why the hooks were never installed

`ci/isa_dump.sh` is the only sanctioned way to disassemble one TU. W1045 lost the
production binary's `.hip_fatbin` to `llvm-objcopy --dump-section` called without
an output path; the script refuses `/data/bin`, always works on a copy, and always
passes an output file.

`ci/install-hooks.sh` existed since W1002 but `pr/k10`'s `.git/hooks` was empty, so
`pre-commit` / `pre-push` (the round gate) never ran in the tree that actually
produces the engine. Installed W1046 after verifying both gates pass locally
(`ci/gate.py --source-only`: 11 checks 0 failed; `ci/round_gate.py --ci`: PASS).

Still missing (needs a policy decision, tracked as R113):
  - `paths:` does not include `tools/**`, so changes to the local gate scripts do
    not trigger this workflow;
  - the three working branches (`gfx906/lcpp-k10`, `gfx906/attn-opt`,
    `gfx906/dot48`) are not in the branch whitelist, so pushes to them produce no run;
  - `deploy/` and `albus/` are not under version control at all.
