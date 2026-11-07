#!/bin/bash
# W836: apply our patches onto upstream head (idempotent where a patcher exists)
F=/home/albus/strata166/pr/strata-fork
S=/home/albus/strata166/src028
cd $F || exit 1
echo "=== A. three files upstream did not touch since v0.2.8 -> take src028's version ==="
for f in serve/telemetry.py serve/web/app.css serve/web/app.js; do
  cp -a "$S/$f" "$F/$f"
  echo "  copied $f"
done
echo
echo "=== B. CMakeLists.txt: re-run the idempotent patcher on upstream's own copy ==="
cp -a CMakeLists.txt /tmp/CMakeLists.upstream
python3 /home/albus/strata166/tmp/restore_cmake.py "$F/CMakeLists.txt" 2>&1 | tail -8
echo
echo "=== C. what changed (should be only our patches) ==="
git diff --stat
echo
echo "=== D. line-level audit: CMakeLists.txt ==="
git diff -U0 -- CMakeLists.txt | grep -E '^[+-][^+-]' | head -30
echo
echo "=== E. the other three: confirm small and expected ==="
for f in src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js; do
  n=$(git diff -U0 -- "$f" | grep -cE '^[+-][^+-]')
  echo "  $f : $n changed lines"
done
