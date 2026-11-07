#!/bin/bash
# [W863] The default branch is now gfx906/mi50, so the scheduler entry point lives there and
# the copy on `main` is dead weight (and breaks main's "clean upstream mirror" property).
set -eu
REPO=/home/albus/strata166/pr/strata-fork
cd "$REPO"

rm -rf /tmp/w863main
git fetch --quiet origin
git worktree add --quiet /tmp/w863main -B w863-main origin/main
cd /tmp/w863main
git rm -q .github/workflows/upstream-watch.yml
git commit -q -F - <<'MSG'
ci: drop the watcher copy from main

The repository's default branch is gfx906/mi50 now, and schedule/workflow_dispatch read
the workflow from the default branch.  Keeping a second copy here only made main differ
from upstream v0.2.9 for no reason.
MSG
git --no-pager log --oneline -1
timeout 120 git push origin HEAD:main 2>&1 | tail -2

cd "$REPO"
git worktree remove --force /tmp/w863main
echo
echo "=== trunk ==="
git rev-parse --abbrev-ref HEAD
git --no-pager log --oneline -1
git status --porcelain --untracked-files=all | wc -l
