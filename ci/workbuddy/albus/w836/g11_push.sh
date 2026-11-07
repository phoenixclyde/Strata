#!/bin/bash
# W836: verify the branch, then push to our GitHub fork
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1

echo "=== A. the branch contains exactly our 5 files ==="
git diff --stat ghup/main..HEAD
echo
echo "=== B. markers present ==="
for m in "W793" "W776" ; do
  printf "  CMakeLists.txt %s: %s\n" "$m" "$(grep -c "$m" CMakeLists.txt)"
done
printf "  qsa_decode_attn.cu W794: %s\n" "$(grep -c 'W794' src/kernels/cuda/qsa_decode_attn.cu)"
printf "  telemetry.py BW_REFRESH_S: %s\n" "$(grep -c 'BW_REFRESH_S' serve/telemetry.py)"
printf "  app.css ALBUS-W831: %s\n" "$(grep -c 'ALBUS-W831' serve/web/app.css)"
printf "  app.js pciePk: %s\n" "$(grep -c 'pciePk' serve/web/app.js)"
echo
echo "=== C. python syntax of the two .py we ship ==="
python3 -m py_compile serve/telemetry.py && echo "  serve/telemetry.py OK" || echo "  serve/telemetry.py FAIL"
echo
echo "=== D. push to origin ==="
git push -u origin gfx906/0.2.8-mi50 2>&1 | tail -12
echo
echo "=== E. remote tracking ==="
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>&1
git log --oneline -1 origin/gfx906/0.2.8-mi50 2>&1
