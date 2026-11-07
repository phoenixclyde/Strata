#!/bin/bash
# W835: pin down the three gaps precisely
S=/home/albus/strata166/src028/src/kernels/cuda
cd $S
echo "=== A. router: block geometry (wave64 half-idle?) ==="
grep -nE "__global__ void route|dim3|<<<|blockDim|constexpr int" native_router.cu | head -20
echo "--- launch sites in the host code ---"
grep -rn "route<<<\|route_multi<<<\|route_topk<<<" ../.. 2>/dev/null | head -8
echo
echo "=== B. native_mmvq: fp16 (unquantized) path — does it use v_dot2? ==="
grep -nE "f16|half|__half|float2|h2" native_mmvq.cu | grep -iE "dot|fma|acc|mul" | head -20
echo "--- how many distinct fetch widths: 128-bit loads? ---"
grep -nE "uint4|float4|int4|__ldg|reinterpret_cast<const uint4" native_mmvq.cu | head -12
echo
echo "=== C. the GDN fp16-as-fp32 trick, full context ==="
sed -n '100,130p' fused_gdn.cu
echo
echo "=== D. native_flash_attn / qsa_score: fp16 dot path ==="
grep -nE "fmaf|__hfma|dot2|half2" native_qsa_score.cu native_flash_attn.cu 2>/dev/null | head -15
echo
echo "=== E. where is PROMPT_F16 / f16 gemm decided ==="
grep -rn "HIP_PROMPT_F16\|PROMPT_F16" ../../../src 2>/dev/null | head -8
