#!/bin/bash
# Overlay ON attempt: configure + build a couple of TUs, capture the exact overlay errors.
set -u
H=/home/albus/strata166
mkdir -p "$H/build-r29b"
LOG=$H/data/w970b.log

docker run --rm \
  -v "$H/pr/strata-fork":/src -v "$H/build-r29b":/out -v "$H/ref/llama_b12099":/ref \
  -w /out strata-gfx906:0.2.10-101 \
  cmake /src -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DSTRATA_GGML_DIR=/ref -DSTRATA_ENABLE_CUDA=ON -DSTRATA_HIP_GFX906=ON \
    -DSTRATA_AMD_COMMUNITY_TUNING=ON -DSTRATA_MMQ_KQUANTS=ON \
    -DSTRATA_MMQ_TQ_OVERLAY=ON -DSTRATA_MMQ_TAB=OFF -DSTRATA_PREFILL_MMQ=OFF \
    -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_Q6K_EXPERTS=ON -DSTRATA_BUILD_TESTS=OFF \
    -DCMAKE_HIP_ARCHITECTURES=gfx906 > "$LOG" 2>&1
echo "CFG_RC=$?"
grep -E "trellis|ggml version|Configuring done|CMake Error" "$LOG" | head -4

docker run --rm \
  -v "$H/pr/strata-fork":/src -v "$H/build-r29b":/out -v "$H/ref/llama_b12099":/ref \
  -v "$H/data":/data -w /out strata-gfx906:0.2.10-101 \
  bash -lc 'nice -n 10 ninja -j6 CMakeFiles/strata_mmq.dir/ref/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu.o > /data/w970b_build.log 2>&1; echo TU_RC=$?'
grep -nE "error:" "$H/data/w970b_build.log" | head -10
