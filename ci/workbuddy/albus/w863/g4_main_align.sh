#!/bin/bash
# W863 · 把 fork 的 main 对齐到上游 v0.2.9（c62d5e3a），保留我们自己的 docs 提交
# 只动 main 分支，不碰 MI50 支线，不碰工作树（先确认干净）
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== working tree must be clean before switching branches (tracked only; the .bak files are untracked) ==="
git status --porcelain --untracked-files=no
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "ABORT: tracked changes present"; exit 1; fi
echo
echo "=== current ==="
git rev-parse --abbrev-ref HEAD; git rev-parse --short HEAD
echo
echo "=== main: ours vs upstream ==="
echo -n "origin/main: "; git rev-parse --short origin/main
echo -n "upstream/main: "; git rev-parse --short upstream/main
echo "ours on top of upstream:"; git log --oneline upstream/main..origin/main
echo "upstream commits we lack:"; git log --oneline origin/main..upstream/main
echo
echo "=== rebase local main onto upstream/main ==="
git checkout main 2>&1 | tail -2
git rebase upstream/main 2>&1 | tail -6
echo
echo "=== main now ==="
git log --oneline -3
echo
echo "=== push main (our fork only) ==="
timeout 180 git push origin main 2>&1 | tail -4
echo
echo "=== back to the MI50 branch, verify nothing moved ==="
git checkout gfx906/0.2.9-mi50 2>&1 | tail -2
git rev-parse --short HEAD
git status --porcelain
