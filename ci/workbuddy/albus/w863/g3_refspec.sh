#!/bin/bash
# W863 · fork 的分支只在自己仓库维护：把 origin 的 fetch refspec 放宽到全部 heads
# （原来只有 +refs/heads/main，所以本地永远看不到 origin 上的 13 条分支）
# 并且确认：任何 push 都不可能落到上游。
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== before ==="
git config --get-all remote.origin.fetch
git config --get-all remote.upstream.pushurl
git config --get-all remote.ghup.pushurl
echo
git config --replace-all remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
echo "=== after ==="
git config --get-all remote.origin.fetch
echo
echo "=== fetch all our branches ==="
timeout 180 git fetch origin --prune 2>&1 | tail -4
git for-each-ref --format='%(refname:short) %(objectname:short)' refs/remotes/origin | sort
echo
echo "=== upstream is fetch-only (no push refspec, push URL disabled) ==="
git config --get-all remote.upstream.url; git config --get-all remote.upstream.pushurl
echo
echo "=== our branch vs upstream main (must be: 2 ahead, 0 behind) ==="
echo -n "ahead: "; git rev-list --count upstream/main..origin/gfx906/0.2.9-mi50
echo -n "behind: "; git rev-list --count origin/gfx906/0.2.9-mi50..upstream/main
echo -n "base (merge-base) == upstream/main? "
[ "$(git merge-base origin/gfx906/0.2.9-mi50 upstream/main)" = "$(git rev-parse upstream/main)" ] && echo YES || echo NO
