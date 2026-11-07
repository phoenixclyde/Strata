#!/bin/bash
# W835: is the dot2 gap real? read the actual inner loops of decode hot kernels
S=/home/albus/strata166/src028/src/kernels/cuda
cd $S
echo "=== A. native_mmvq.cu: the 23 dot2 hits, in context ==="
grep -n -i "dot2" native_mmvq.cu | head -25
echo
echo "=== B. native_router.cu (router = 8.5% of window): inner loop ==="
grep -nE "__shfl|dpp|fma|half2|__half|acc \+=|dot" native_router.cu | head -30
echo "--- router kernel signature / block size ---"
grep -nE "__global__|dim3|blockDim|WARP|64|32" native_router.cu | head -20
echo
echo "=== C. qsa_decode_attn.cu (13% of window): reduction style ==="
grep -nE "__shfl[_a-z]*|dpp|ds_bpermute|__shared__" qsa_decode_attn.cu | head -30
echo
echo "=== D. gdn / fused_gdn: q8 gemv inner loop ==="
grep -nE "__shfl|dpp|half2|__hfma|dot|acc" fused_gdn.cu | head -25
echo
echo "=== E. is there any fp16 dp4a-style / int8 dot for weights? ==="
grep -rnE "dp4a|__ockl_sdot4|sdot4|v_dot4" *.cu *.cuh 2>/dev/null | head -15
