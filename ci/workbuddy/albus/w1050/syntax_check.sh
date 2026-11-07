#!/bin/bash
# W1050: single-TU syntax check of the generated fused_gdn.cu (full diagnostics).
set -u
W=/home/albus/strata166/tmp/w1050
IMG=strata-gfx906:0.2.11-101
git -C /home/albus/strata166/pr/k10 show gfx906/r114:src/kernels/cuda/fused_gdn.cu > "$W/fg.cu"
docker run --rm \
  -v /home/albus/strata166/pr/k10:/src \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp \
  -v "$W":/w "$IMG" bash -lc '
    clang++ -DSTRATA_HIP_GFX906=1 -DSTRATA_VERSION=\"0.1.57\" \
      -I/src/third_party/ggml -I/src/include \
      -isystem /src/include/strata/platform/hip_compat \
      -std=c++20 --offload-arch=gfx906 -x hip -fsyntax-only /w/fg.cu 2>&1 | head -30
  '
