#!/bin/bash
# [W863] Commit the downstream gate + upstream watcher (new files only), then push.
set -eu
cd /home/albus/strata166/pr/strata-fork

git add ci/gate.py ci/README.md \
        .github/workflows/downstream-gate.yml \
        .github/workflows/upstream-watch.yml

git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com \
  commit -q -m @'ci: add the downstream gate and the upstream watcher

Three new files; no upstream file is touched, so a rebase onto a new upstream version
cannot conflict here.

  ci/gate.py                              config-face checks, 11 without a GPU / 18 on 166
  .github/workflows/downstream-gate.yml   runs it for every change under src/, include/, CMakeLists
  .github/workflows/upstream-watch.yml    daily upstream gap -> one issue, updated in place

Why now: nothing in CI looked at src/, so the R table and the "rollback switch that
existed only in a comment" could both regress without a signal.  Each check in gate.py
maps to a mistake already made here (ci/README.md lists them with the measured cost).

Upstream watch deliberately does not rebase: a push made with GITHUB_TOKEN starts no
workflow, a rebase of a patch stack needs a force-push to the trunk, and this runner has
no GPU to rebuild or verify.  It detects and reminds; the rebase stays a human step.
'@

git --no-pager log --oneline -1
echo "=== changed files ==="
git --no-pager show --stat --oneline HEAD | tail -6
echo "=== clean? ==="
git status --porcelain --untracked-files=all | wc -l
echo "=== push ==="
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2
