#!/bin/bash
# W835: what does Strata's own gfx906 code already do? instruction-level census
S=/home/albus/strata166/src028
echo "=== A. kernel inventory ==="
ls $S/src/kernels/cuda/ 2>/dev/null | head -40
echo "total files:"; ls $S/src/kernels/cuda/*.cu 2>/dev/null | wc -l
echo
echo "=== B. instruction-level census across ALL kernel files ==="
cd $S/src/kernels/cuda
for pat in "__ockl_fdot2" "fdot2" "__hfma2" "dot2" "__builtin_amdgcn_ds_bpermute" "ds_bpermute" "__shfl_xor" "__shfl" "dpp" "__builtin_amdgcn_dpp" "v_mfma" "__builtin_amdgcn_mfma"; do
  tot=$(grep -rho "$pat" *.cu *.cuh 2>/dev/null | wc -l)
  files=$(grep -rl "$pat" *.cu *.cuh 2>/dev/null | wc -l)
  printf "  %-34s hits=%-6s files=%s\n" "$pat" "$tot" "$files"
done
echo
echo "=== C. which files use fdot2 / dot2 (the KI winning pattern) ==="
grep -rln "fdot2\|dot2\|__hfma2" *.cu *.cuh 2>/dev/null | head -20
echo
echo "=== D. LDS declarations: is any padded (+1) ? ==="
grep -rnE "^\s*__shared__" *.cu *.cuh 2>/dev/null | head -40
echo
echo "=== E. LDS with +1 / padding patterns ==="
grep -rnE "\+\s*1\s*\]|\+\s*[A-Za-z_]+\s*\]\s*;|pad" *.cu *.cuh 2>/dev/null | grep -iE "shared|lds|pad" | head -20
