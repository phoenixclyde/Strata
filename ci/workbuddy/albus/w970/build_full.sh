#!/bin/bash
# Full build of the merged tree against upstream 0.8.0 with PRODUCTION parity, overlay ON.
set -u
H=/home/albus/strata166
MODE=$1          # "on" or "off"
DIR=$2           # build dir
OVERLAY=ON; [ "$MODE" = "off" ] && OVERLAY=OFF
mkdir -p "$H/$DIR"

docker run --rm \
  -v "$H/pr/strata-fork":/src -v "$H/$DIR":/out -v "$H/ref/llama_b12099":/ref \
  -w /out strata-gfx906:0.2.10-101 \
  cmake /src -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DSTRATA_GGML_DIR=/ref -DSTRATA_ENABLE_CUDA=ON -DSTRATA_HIP_GFX906=ON \
    -DSTRATA_AMD_COMMUNITY_TUNING=ON -DSTRATA_MMQ_KQUANTS=ON \
    -DSTRATA_MMQ_TQ_OVERLAY=$OVERLAY -DSTRATA_MMQ_TAB=OFF -DSTRATA_PREFILL_MMQ=OFF \
    -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_Q6K_EXPERTS=ON -DSTRATA_BUILD_TESTS=OFF \
    -DCMAKE_HIP_ARCHITECTURES=gfx906 > "$H/data/w970_${MODE}_cfg.log" 2>&1
echo "CFG_RC=$? overlay=$OVERLAY"
grep -E "tern|ggml version|Configuring done" "$H/data/w970_${MODE}_cfg.log" | tail -2

docker run --rm \
  -v "$H/pr/strata-fork":/src -v "$H/$DIR":/out -v "$H/ref/llama_b12099":/ref \
  -v "$H/data":/data -w /out strata-gfx906:0.2.10-101 \
  bash -lc "nice -n 10 ninja -j6 strata > /data/w970_${MODE}_build.log 2>&1; echo BUILD_RC=\$?; grep -c 'error:' /data/w970_${MODE}_build.log; ls -l strata 2>/dev/null | awk '{print \$5}'"
