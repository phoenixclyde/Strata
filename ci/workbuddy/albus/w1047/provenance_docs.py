import io
import pathlib

OUT = pathlib.Path(r"D:/workbuddy_space/strata_ws/albus/w1047/bundle/stage/ci/provenance")
OUT.mkdir(parents=True, exist_ok=True)

history = """# CI/CD provenance and corrections (W1047)

This file records what W1045/W1046 got right, what was wrong, and what is now enforced.

## Corrections to prior rounds

1. **W1045: "`pr/k10` has no pre-push hook" was only half-true.**
   `pr/k10` is a linked worktree, so `.git` is a pointer file and `.git/hooks` is
   not the active hook directory. The hook scripts existed in the repo since
   W1002, and the shared hooks directory is
   `/home/albus/strata166/pr/strata-fork/.git/hooks`. W1046 added
   `ci/install-hooks.sh` support for `git rev-parse --git-common-dir` and
   installed the hooks; both `pre-commit` and `pre-push` call `ci/round_gate.py`.
2. **W1045: "CI zero trigger today" became stale after 18:51.**
   GitHub API shows successful `Downstream gate` runs for `eb5bfbb8`
   (`ci/w1046-gates`) and `b2c82ff0` (`ci/w1046-hooks`) at 2026-11-07T10:51Z.
   The earlier conclusion was correct at the time for production/candidate
   commits, because those branches were outside the workflow whitelist.
3. **`round_gate.py --status` was still wrong after the hooks were installed.**
   It checked `ROOT/.git/hooks`, which cannot work in a linked worktree. W1047
   changes the check to `git rev-parse --git-path hooks`, matching the installed
   shared hooks.
4. **`tools/`, `deploy/params/`, `albus/` and `waves/` were not versioned.**
   This is no longer a hidden local-only gap: the active scripts are copied into
   `ci/workbuddy/**`, and every auditable workspace file has a SHA-256 row in
   `workspace_manifest.tsv`. Historical fork/source snapshots are excluded from
   the repository but remain hash-auditable.

## Current CI topology

- GitHub Actions is **static-only** by design: syntax checks and self-tests, no
  ROCm build, no GPU benchmark, no production install.
- The pre-push hook is the local enforcement point for every push from the
  source worktree.
- The deploy evidence gate remains the install-time enforcement point.
- The WorkBuddy round gate is the end-of-answer enforcement point.

## Remaining honest limits

- The 2 GiB historical workspace is not copied wholesale into GitHub. The
  manifest is the retroactive audit trail; it proves omissions are deliberate
  and detectable.
- Exact production binaries from older rounds cannot always be rebuilt when
  their source snapshots were discarded. `REBUILD_RECIPE.tsv` marks LOST rows.
- A GitHub run on `gfx906/hc-dp4a` proves the static surface only. B3 still
  requires the explicit GPU timing/numeric window before install.
"""
(OUT / "HISTORY_CORRECTIONS.md").write_text(history, encoding="utf-8", newline="\n")

readme = """# Provenance

- `workspace_manifest.tsv` - SHA-256 of every auditable WorkBuddy workspace file.
- `selected_scripts.tsv` - SHA-256 of every script/patch copied into `ci/workbuddy`.
- `HISTORY_CORRECTIONS.md` - corrections to W1045/W1046 CI claims and current limits.

Regenerate from the WorkBuddy workspace with `albus/w1047/build_bundle.py`.
The GitHub workflow cannot see the laptop workspace, so the checked-in manifest
is the bridge between local artifacts and CI-visible provenance.
"""
(OUT / "README.md").write_text(readme, encoding="utf-8", newline="\n")
print("provenance docs written")
