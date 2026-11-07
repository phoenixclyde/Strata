#!/bin/bash
set -u
SRC=~/strata166/pr/strata-fork
W=~/strata166/work/r66

echo "=== 生成 R68 补丁（只要 generate.cpp + 新头）==="
cd $SRC || exit 1
git show 243fdb21 -- src/program/generate.cpp include/strata/core/serve_stop_bound.hpp > /tmp/r68.patch
wc -l /tmp/r68.patch

echo
echo "=== 我方 generate.cpp 被上游动过几次（冲突面）==="
MB=$(git merge-base HEAD upstream/main 2>/dev/null)
echo "merge-base=$(git log -1 --format='%h' $MB 2>/dev/null)"
git log --oneline $MB..HEAD -- src/program/generate.cpp | wc -l

echo
echo "=== dry-run ==="
cd $W || exit 1
patch -p1 --dry-run < /tmp/r68.patch 2>&1 | head -12

echo
echo "=== 我方 generate.cpp 里已有的相关上下文 ==="
grep -n "STRATA_MTP_TOP2\|chain_kind = 0" src/program/generate.cpp | head -5
