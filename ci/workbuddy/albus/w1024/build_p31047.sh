#!/bin/bash
# Build b12129 + #31047 using a git worktree (so the mainline checkout is never touched).
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
WT=/tmp/wt-b12169
LC=/home/albus/strata166/ref/llama_b12129_p31047
NEW=/home/albus/strata166/build-lcpp

cd "$R" || exit 3
git worktree remove --force "$WT" 2>/dev/null || true
git worktree add -f "$WT" exp/lcpp-b12129 >/dev/null 2>&1 || { echo WORKTREE_FAIL; exit 4; }
echo "worktree: $(git -C "$WT" rev-parse --short HEAD) $(git -C "$WT" rev-parse --abbrev-ref HEAD)"

docker run --rm --security-opt label=disable \
  -v "$WT":/src -v "$NEW":/out -v "$LC":/llama.cpp \
  strata-gfx906:0.2.11-101 bash -lc '
cd /out
find . -name "*.o" -delete 2>/dev/null
find . -name "*.a" -delete 2>/dev/null
rm -f strata
cmake -DSTRATA_GGML_DIR=/llama.cpp . > /tmp/cm4.log 2>&1
echo "cmake rc=$?"; tail -2 /tmp/cm4.log
ninja -j6 strata > /tmp/nj4.log 2>&1
echo "ninja rc=$?  errors=$(grep -c "error:" /tmp/nj4.log)"
grep "error:" /tmp/nj4.log | head -8
ls -l strata 2>/dev/null; md5sum strata 2>/dev/null; ./strata --version 2>/dev/null
'
echo "=== worktree remove"
cd "$R" && git worktree remove --force "$WT" 2>/dev/null
git -C "$R" status --porcelain | wc -l
