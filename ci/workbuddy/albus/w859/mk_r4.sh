#!/bin/bash
# W859：R4（#4158 STRATA_PF_MMVQ）移植到 gfx906/pf-mmvq 并编译（只编译，不部署）
set -u
cd /home/albus/strata166/gfx029
git worktree add -B gfx906/pf-mmvq /home/albus/strata166/gfx-mmvq aef9d256 2>&1 | tail -2
cd /home/albus/strata166/gfx-mmvq
MB=$(git merge-base HEAD refs/remotes/upstream/pr4158)
echo "merge-base=$MB"
LIST=$(git rev-list --reverse "$MB..refs/remotes/upstream/pr4158")
echo "commits:"; echo "$LIST"
for c in $LIST; do
  git cherry-pick -x "$c" 2>&1 | tail -3
  rc=$?
  echo "--- pick $c rc=$rc"
  [ $rc -ne 0 ] && { echo "CHERRY-PICK FAILED at $c"; git status --porcelain | head -10; exit 1; }
done
echo "=== 结果 ==="
git log --oneline -4
git diff --stat aef9d256..HEAD | tail -7
grep -rn 'STRATA_PF_MMVQ' src/prefill/gemm.cu CMakeLists.txt 2>/dev/null | head -5
