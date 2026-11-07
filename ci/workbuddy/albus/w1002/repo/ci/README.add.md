
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
| round closing (laptop) | `tools/round_close.py` | `report_lint` FAIL, `plan_lint` FAIL, missing four-section report |

Negative self-tests are mandatory: `round_gate.py --ci` runs `report_lint` against
both a complete four-section report (**must PASS**) and a conclusion-only text
(**must FAIL**). A lint that always passes is worse than no lint.

Local-only scripts (they hardcode Windows paths) stay on the laptop:
`report_lint.py`, `ledger_lint.py`, `param_pair_lint.py`, `plan_lint.py`,
`round_close.py`. The repo copy `ci/report_lint.py` is kept byte-identical to
`tools/report_lint.py`; `verify.py` checks it exists.
