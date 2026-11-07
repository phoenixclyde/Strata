#!/bin/bash
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
WT=/tmp/wt-r99
LC=/home/albus/strata166/ref/llama_b12129_p31047
NEW=/home/albus/strata166/build-lcpp

cd "$R" || exit 3
git worktree remove --force "$WT" 2>/dev/null || true
git worktree add -f "$WT" exp/lcpp-b12169 >/dev/null 2>&1 || { echo WORKTREE_FAIL; exit 4; }
echo "worktree $(git -C "$WT" rev-parse --short HEAD)"

docker run --rm --security-opt label=disable \
  -v "$WT":/src -v "$NEW":/out -v "$LC":/llama.cpp \
  strata-gfx906:0.2.11-101 bash -lc '
cd /out
find . -name "*.o" -delete 2>/dev/null
find . -name "*.a" -delete 2>/dev/null
rm -f strata
cmake -DSTRATA_GGML_DIR=/llama.cpp . > /tmp/cm5.log 2>&1
echo "cmake rc=$?"
ninja -j6 strata > /tmp/nj5.log 2>&1
echo "ninja rc=$?  errors=$(grep -c "error:" /tmp/nj5.log)"
grep "error:" /tmp/nj5.log | head -8
ls -l strata 2>/dev/null; md5sum strata 2>/dev/null; ./strata --version 2>/dev/null
'
cd "$R" && git worktree remove --force "$WT" 2>/dev/null
echo "main dirty=$(git -C "$R" status --porcelain | wc -l)"
