#!/bin/bash
# W835c: the two arch tables verbatim + the gates for the most promising "not-written" items
S=/home/albus/strata166/src028
cd $S || exit 1
echo "=== A. arch_defaults.cpp : gfx12 (RDNA4) table ==="
sed -n '25,56p' src/core/arch_defaults.cpp | cut -c1-200
echo
echo "=== B. arch_defaults.cpp : gfx1151 table ==="
sed -n '56,95p' src/core/arch_defaults.cpp | cut -c1-200
echo
echo "=== C. HC_UPMIX implementation gate ==="
grep -rn "hc_upmix\|HC_UPMIX" src include 2>/dev/null | grep -v arch_defaults | head -8
echo "--- its arch gate, if any ---"
f=$(grep -rln "hc_upmix" src include 2>/dev/null | grep -v arch_defaults | head -1); echo "file=$f"
[ -n "$f" ] && grep -nE "gfx_arch_is|__HIPCC__|__CUDA_ARCH__|#if |wmma" "$f" | head -12
echo
echo "=== D. dequant_wide : per-card default ==="
sed -n '280,320p' src/kernels/cuda/dequant_bf16.cu | cut -c1-190
echo
echo "=== E. GRAPH_PRIO : the HIP branch ==="
sed -n '196,240p' src/core/verify.cpp | cut -c1-190
