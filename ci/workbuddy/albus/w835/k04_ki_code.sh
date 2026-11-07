#!/bin/bash
# W835: what gfx906-specific techniques does KI actually use, at instruction level
K=/home/albus/routeK/base/KIntegrated-mobydick
echo "=== A. fattn-q8.cuh: size + gfx906 markers ==="
F=$K/csrc/gfx906_fa/kernel/fattn-q8.cuh
wc -l $F
echo "--- marker counts ---"
for pat in "ds_bpermute" "__shfl" "dpp" "DOT2\|dot2" "v_dot" "__builtin_amdgcn" "lds\|__shared__" "wave64\|WAVE\|64" "__fp16\|half2"; do
  n=$(grep -c -iE "$pat" $F 2>/dev/null)
  echo "  $pat = $n"
done
echo
echo "--- LDS layout declarations (padding evidence) ---"
grep -nE "^\s*(__shared__|extern __shared__)|\[[A-Z0-9_]+\]\s*\[[A-Z0-9_]+\+1\]|\+ *1 *\]" $F | head -20
echo
echo "--- the dot2 / fp16 inline asm or intrinsics ---"
grep -nE "amdgcn|dot2|__hfma2|__half2|float2" $F | head -20
echo
echo "=== B. dense_gemv_gfx906.cu: what it does ==="
G=$K/csrc/rocm/dense_gemv_gfx906.cu
wc -l $G
head -60 $G
echo
echo "=== C. config header ==="
cat $K/csrc/gfx906_fa/kernel/gfx906-config.h
