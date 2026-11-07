#!/bin/bash
# W835c: what exactly do the gfx11x branches in prefill/kernels.cu and qsa_select.cu do?
S=/home/albus/strata166/src028/src
cd $S || exit 1
echo "=== A. prefill/kernels.cu : the gfx11 branches ==="
grep -nE "gfx_arch_is|gfx11|gfx12|wmma|WMMA|__CUDA_ARCH__" prefill/kernels.cu 2>/dev/null | head -30
echo
echo "=== B. qsa_select.cu : the gfx11/gfx12 branches ==="
grep -nE "gfx_arch_is|gfx11|gfx12|__CUDA_ARCH__" kernels/cuda/qsa_select.cu 2>/dev/null | head -30
echo
echo "=== C. gfx_arch.hpp : predicate list (no gfx906?) ==="
grep -nE "inline bool|gfx_arch_is|^// " include/strata/kernels/gfx_arch.hpp 2>/dev/null | head -40
echo
echo "=== D. how qsa_decode_attn names gfx906 (the pattern we'd copy) ==="
grep -nE "gfx906" kernels/cuda/qsa_decode_attn.cu 2>/dev/null | head -18
