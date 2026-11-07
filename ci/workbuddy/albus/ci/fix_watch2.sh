#!/bin/bash
# [W863] Finish what fix_watch.sh started.  Two mistakes to undo:
#   1. commit messages were written as   -m @'...'@   which bash reads as "@"+string+"@",
#      so every message we pushed starts with a stray '@'.  Use -F - (stdin) instead.
#   2. an apostrophe inside such a message ("scheduler's") closed the quote early and the
#      rest was parsed as pathspecs -> commit failed, worktree left behind.
set -eu
REPO=/home/albus/strata166/pr/strata-fork
cd "$REPO"

echo "=== cleanup any leftover worktree ==="
git worktree list
rm -rf /tmp/w863main
git worktree prune
git worktree list

echo
echo "=== amend the just-pushed message (no code change) ==="
git log -1 --format='before: %s'
git commit --amend -q -F - <<'MSG'
ci(watch): check out gfx906/mi50 explicitly

schedule and workflow_dispatch only run a workflow that exists on the default branch,
so a copy of this file goes to main.  Without an explicit ref that copy would compare
main against upstream (always 0 behind) and never report anything.
MSG
git log -1 --format='after : %s'
timeout 120 git push --force-with-lease origin gfx906/mi50 2>&1 | tail -1

echo
echo "=== place the copy on main via a throwaway worktree ==="
git fetch --quiet origin
git worktree add --quiet /tmp/w863main -B w863-main origin/main
cp -f .github/workflows/upstream-watch.yml /tmp/w863main/.github/workflows/upstream-watch.yml
cd /tmp/w863main
git add .github/workflows/upstream-watch.yml
git commit -q -F - <<'MSG'
ci: run the upstream watcher from the default branch

GitHub schedules and dispatches a workflow only when the file exists on the default
branch.  This copy is the scheduler's entry point; it checks out gfx906/mi50 explicitly,
so what it measures is the trunk we deploy, not main.
MSG
git --no-pager log --oneline -1
git --no-pager show --stat --oneline HEAD | tail -3
timeout 120 git push origin HEAD:main 2>&1 | tail -2

cd "$REPO"
git worktree remove --force /tmp/w863main
echo
echo "=== trunk state ==="
git rev-parse --abbrev-ref HEAD
git --no-pager log --oneline -2
git status --porcelain --untracked-files=all | wc -l
