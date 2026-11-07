#!/bin/bash
# W863 · 把 fork 的 main 换成「v0.2.9 + 我们的 docs 提交」，推回 fork（force-with-lease 有保护）
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
OLD=9c369f15
echo "=== guard: remote main must still be $OLD ==="
git fetch origin main 2>&1 | tail -2
CUR=$(git rev-parse origin/main)
echo "origin/main = $CUR"
[ "${CUR:0:8}" = "$OLD" ] || { echo "ABORT: origin/main moved"; exit 1; }
echo
echo "=== move local main to the aligned commit ==="
git branch -f main w863/main-align
git checkout main 2>&1 | tail -2
git log --oneline -3
echo
echo "=== push with lease (our fork only; upstream push is disabled) ==="
timeout 180 git push --force-with-lease=main:$OLD origin main 2>&1 | tail -4
echo
echo "=== verify remote ==="
git ls-remote --heads origin main
echo
echo "=== relationships after the fix ==="
echo -n "main ahead of upstream: "; git rev-list --count upstream/main..main
echo -n "main behind upstream: ";  git rev-list --count main..upstream/main
echo -n "MI50 branch ahead of main: "; git rev-list --count main..gfx906/0.2.9-mi50
echo -n "MI50 branch behind main: ";  git rev-list --count gfx906/0.2.9-mi50..main
echo -n "tag v0.2.9 = upstream/main: "; [ "$(git rev-parse v0.2.9)" = "$(git rev-parse upstream/main)" ] && echo YES || echo NO
echo
echo "=== back to the MI50 branch, clean ==="
git checkout -f gfx906/0.2.9-mi50 2>&1 | tail -2
git rev-parse --abbrev-ref HEAD; git rev-parse --short HEAD
git status --porcelain --untracked-files=no
git branch -D w863/main-align 2>&1 | tail -1
