#!/bin/bash
# W863 · 修浅克隆：补全历史（后台跑，不动工作树）
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== before ==="
echo -n "shallow: "; git rev-parse --is-shallow-repository
echo -n "shallow file lines: "; wc -l < .git/shallow
echo -n "commits reachable: "; git rev-list --count HEAD 2>/dev/null | head -1
echo -n "partial clone filter: "; git config --get remote.origin.partialclonefilter || echo "(none)"
echo
echo "=== unshallow from upstream (the real source of history) ==="
timeout 1700 git fetch --unshallow upstream 2>&1 | tail -8
echo "rc=$?"
echo
echo "=== after ==="
echo -n "shallow: "; git rev-parse --is-shallow-repository
echo -n "shallow file lines: "; (wc -l < .git/shallow 2>/dev/null || echo 0)
echo -n "commits reachable: "; git rev-list --count HEAD 2>/dev/null
echo -n "merge-base(main, upstream/main): "; git merge-base main upstream/main 2>&1 | cut -c1-12
du -sh .git
