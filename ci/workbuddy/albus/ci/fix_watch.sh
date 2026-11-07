#!/bin/bash
# [W863] Fix the watcher's ref, commit on the trunk, and place the copy on `main` so that
# the daily schedule actually runs (GitHub only schedules workflows that exist on the
# default branch -- the file's own comment says so).
set -eu
cd /home/albus/strata166/pr/strata-fork

echo "=== 1. commit the ref fix on gfx906/mi50 ==="
git add .github/workflows/upstream-watch.yml
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com \
  commit -q -m "$(cat <<'MSG'
ci(watch): check out gfx906/mi50 explicitly

schedule/workflow_dispatch only run a workflow that exists on the default branch, so a
copy of this file goes to main.  Without an explicit ref that copy would compare main
against upstream (always 0 behind) and never report anything.
MSG
)"
git --no-pager log --oneline -1
timeout 120 git push origin gfx906/mi50 2>&1 | tail -1

echo
echo "=== 2. put the same file on main (separate worktree; the trunk stays untouched) ==="
rm -rf /tmp/w863main
git fetch --quiet origin
git worktree add --quiet /tmp/w863main -B w863-main origin/main
cp -f .github/workflows/upstream-watch.yml /tmp/w863main/.github/workflows/upstream-watch.yml
cd /tmp/w863main
git add .github/workflows/upstream-watch.yml
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com \
  commit -q -m "$(cat <<'MSG'
ci: run the upstream watcher from the default branch

GitHub schedules and dispatches a workflow only when the file exists on the default
branch.  This copy is the scheduler's entry point; it checks out gfx906/mi50 explicitly,
so what it measures is the trunk we deploy, not main.
MSG
)"
git --no-pager log --oneline -1
git --no-pager show --stat --oneline HEAD | tail -3
timeout 120 git push origin HEAD:main 2>&1 | tail -2
cd /
cd /home/albus/strata166/pr/strata-fork
git worktree remove --force /tmp/w863main
echo "worktree removed"
echo
echo "=== 3. back on the trunk? ==="
git rev-parse --abbrev-ref HEAD
git status --porcelain --untracked-files=all | wc -l
