#!/bin/bash
# W836: get upstream main at depth 1 and create our branch
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
echo "=== A. clear any stuck fetch ==="
pkill -f "git fetch upstream" 2>/dev/null; sleep 2
rm -f .git/index.lock 2>/dev/null
echo "before: upstream/main = $(git rev-parse --short upstream/main 2>&1)"
echo
echo "=== B. shallow fetch of upstream main ==="
timeout 420 git fetch upstream main --depth=1 --no-tags 2>&1 | tail -5
echo "FETCH_HEAD = $(git rev-parse --short FETCH_HEAD 2>&1)"
echo
echo "=== C. confirm the tree has the files we patch ==="
for f in CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js; do
  s=$(git cat-file -s FETCH_HEAD:$f 2>/dev/null || echo MISSING)
  echo "  $f = $s bytes"
done
