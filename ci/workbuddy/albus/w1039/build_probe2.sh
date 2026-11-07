#!/bin/bash
# W1039: build + run probe #2 (cancellation amplification).  File, not inline command (twice bitten).
set -u
C=/opt/rocm/lib/llvm/bin/clang++
SRC=${1:-/w/t_probe2.cu}
OUT=${2:-/w/t_probe2}
$C -x hip --offload-arch=gfx906 -O3 -w -o "$OUT" "$SRC" > /w/probe2_build.log 2>&1
echo "BUILD_RC=$?"
grep -m4 error: /w/probe2_build.log
ls -l "$OUT" 2>&1 | tail -1
if [ "${3:-}" = "run" ]; then
  echo "=== run ==="
  "$OUT"
  echo "RUN_RC=$?"
fi
