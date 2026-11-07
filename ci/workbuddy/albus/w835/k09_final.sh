#!/bin/bash
# W835: the 32-only gate, and KI's fdot2 template
S=/home/albus/strata166/src028/src/kernels/cuda
K=/home/albus/routeK/base/KIntegrated-mobydick
echo "=== A. fused_gr.cu: what kernel refuses warpSize != 32 ==="
sed -n '3085,3120p' $S/fused_gr.cu
echo
echo "=== B. its caller / fallback ==="
grep -n "gr_norm_split_fast\|norm_fast_on\|warpSize" $S/fused_gr.cu | head -20
echo
echo "=== C. KI dense_gemv: the exact fdot2 template ==="
grep -n -B3 -A12 "__ockl_fdot2" $K/csrc/rocm/dense_gemv_gfx906.cu | head -40
echo
echo "=== D. KI moe_q_gemm: same pattern? ==="
grep -n -B2 -A6 "__ockl_fdot2" $K/csrc/rocm/moe_q_gemm_gfx906.cu | head -30
echo
echo "=== E. KI: does it also use DPP explicitly? ==="
for f in $K/csrc/gfx906_fa/kernel/*.cuh $K/csrc/rocm/*gfx906*.cu; do
  n=$(grep -c "dpp\|DPP" $f 2>/dev/null)
  [ "$n" -gt 0 ] && echo "  $(basename $f): $n"
done
