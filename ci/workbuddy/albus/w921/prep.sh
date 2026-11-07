#!/bin/bash
set -u
SRC=~/strata166/pr/strata-fork
W=~/strata166/work/r66

echo "=== 1. 复制源码树（保留 mtime，排除 .git）==="
rm -rf $W && mkdir -p $W
rsync -a --exclude=.git $SRC/ $W/
echo "files=$(find $W -type f | wc -l)  size=$(du -sh $W | cut -f1)"

echo
echo "=== 2. 生成三个补丁（只取需要的路径）==="
cd $SRC || exit 1
git show fbf6e1c7 -- src/prefill/prefill.cpp > /tmp/r66_p1.patch
git show 5273fb66 -- src/prefill/prefill.cpp include/strata/prefill/routed_stream.hpp > /tmp/r66_p2.patch
git show 3cc47f02 -- src/prefill/prefill.cpp > /tmp/r66_p3.patch
wc -l /tmp/r66_p*.patch

echo
echo "=== 3. 逐个 dry-run ==="
cd $W || exit 1
for p in /tmp/r66_p1.patch /tmp/r66_p2.patch /tmp/r66_p3.patch; do
  echo "--- $p ---"
  patch -p1 --dry-run < $p 2>&1 | head -6
done
