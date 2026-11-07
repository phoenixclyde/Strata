#!/bin/bash
# Build the merged deployment tree against upstream llama.cpp 0.8.0 with production's flags (build-r28 parity).
set -u
cd /home/albus/strata166
mkdir -p build-r29
docker run --rm \
  -v /home/albus/strata166/pr/strata-fork:/src \
  -v /home/albus/strata166/build-r29:/out \
  -v /home/albus/strata166/ref/llama_b12099:/ref \
  -v /home/albus/strata166/data:/data \
  -w /out strata-gfx906:0.2.10-101 \
  cmake /src -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DSTRATA_GGML_DIR=/ref -DSTRATA_ENABLE_CUDA=ON -DSTRATA_HIP_GFX906=ON \
    -DSTRATA_AMD_COMMUNITY_TUNING=ON -DSTRATA_MMQ_KQUANTS=ON \
    -DSTRATA_MMQ_TQ_OVERLAY=OFF -DSTRATA_MMQ_TAB=OFF -DSTRATA_PREFILL_MMQ=OFF \
    -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_Q6K_EXPERTS=ON -DSTRATA_BUILD_TESTS=OFF \
    -DCMAKE_HIP_ARCHITECTURES=gfx906 > /data/w970_cfg.log 2>&1
echo "CFG_RC=$?"
grep -E "ggml version|trellis|Configuring done" /data/w970_cfg.log | head -3
docker run --rm \
  -v /home/albus/strata166/pr/strata-fork:/src \
  -v /home/albus/strata166/build-r29:/out \
  -v /home/albus/strata166/ref/llama_b12099:/ref \
  -v /home/albus/strata166/data:/data \
  -w /out strata-gfx906:0.2.10-101 \
  bash -lc 'nice -n 10 ninja -j6 strata > /data/w970_build.log 2>&1; echo BUILD_RC=$?; grep -c "error:" /data/w970_build.log; ls -l strata'
