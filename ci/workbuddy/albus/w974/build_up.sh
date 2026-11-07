#!/bin/bash
# Build strata against a given upstream tree with PRODUCTION parity (overlay ON).
# usage: build_up.sh <ref_dir_name> <build_dir_name>
set -u
H=/home/albus/strata166
REF=$1
DIR=$2
mkdir -p "$H/$DIR"
LOG_IN=/data/$(basename "$DIR")_build.log      # 容器内路径
LOG=$H/data/$(basename "$DIR")_build.log       # 宿主路径
CFG=$H/data/$(basename "$DIR")_cfg.log

docker run --rm \
  -v "$H/pr/strata-fork":/src -v "$H/$DIR":/out -v "$H/ref/$REF":/ref \
  -w /out strata-gfx906:0.2.10-101 \
  cmake /src -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DSTRATA_GGML_DIR=/ref -DSTRATA_ENABLE_CUDA=ON -DSTRATA_HIP_GFX906=ON \
    -DSTRATA_AMD_COMMUNITY_TUNING=ON -DSTRATA_MMQ_KQUANTS=ON \
    -DSTRATA_MMQ_TQ_OVERLAY=ON -DSTRATA_MMQ_TAB=OFF -DSTRATA_PREFILL_MMQ=OFF \
    -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_Q6K_EXPERTS=ON -DSTRATA_BUILD_TESTS=OFF \
    -DCMAKE_HIP_ARCHITECTURES=gfx906 > "$CFG" 2>&1
echo "CFG_RC=$?"
grep -E "ggml version|Configuring done|CMake Error|overlay" "$CFG" | tail -4

docker run --rm \
  -v "$H/pr/strata-fork":/src -v "$H/$DIR":/out -v "$H/ref/$REF":/ref \
  -v "$H/data":/data -w /out strata-gfx906:0.2.10-101 \
  bash -lc "nice -n 10 ninja -j6 strata > $LOG_IN 2>&1; echo BUILD_RC=\$?; grep -c 'error:' $LOG_IN; ls -l strata 2>/dev/null | awk '{print \$5}'"
