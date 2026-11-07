#!/bin/bash
# W858 A 线：在 gfx906/routed-stream（#4283 两提交已 cherry-pick）上编译
#   1) routed_stream_test（header-only no-GPU 单测，先证明移植正确）
#   2) strata 引擎（供随后 A/B）
# 与生产同配方（W844 build.sh）：只换源码树与输出目录，不部署。
set -u
S=/home/albus/strata166/gfx-mmvq
O=/home/albus/strata166/gfx-mmvq-build
G=/home/albus/strata166/src028/third_party/llama.cpp
LOG=/home/albus/strata166/data/w859_build_mmvq.log
IMG=strata-gfx906:0.2.8p2
mkdir -p "$O"; : > "$LOG"
{
  echo "=== build start $(date +%F' '%T)"
  docker run --rm --name strata-w859build \
    -v "$S":/src -v "$O":/out -v "$G":/llama.cpp:ro \
    "$IMG" bash -lc "
set -u
cd /src
cmake -S . -B /out -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_ENABLE_CUDA=ON -DSTRATA_ENABLE_HIP=OFF -DSTRATA_ENABLE_SYCL=OFF \
  -DSTRATA_GGML_DIR=/llama.cpp \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_DSV41=OFF \
  -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_PREFILL_MMQ=OFF \
  -DSTRATA_Q6K_EXPERTS=OFF -DSTRATA_WERROR=OFF
rc=\$?; echo \"--- configure rc=\$rc\"; [ \$rc -ne 0 ] && exit \$rc
echo '--- ninja routed_stream_test'
nice -n 15 ninja -C /out -j 8 routed_stream_test
rc=\$?; echo \"--- test build rc=\$rc\"
if [ \$rc -eq 0 ]; then echo '--- RUN routed_stream_test'; /out/routed_stream_test 2>&1 | tail -20; echo \"--- test run rc=\$?\"; fi
echo '--- ninja strata'
nice -n 15 ninja -C /out -j 10 strata
rc=\$?; echo \"--- ninja rc=\$rc\"; [ \$rc -ne 0 ] && exit \$rc
/out/strata --version 2>&1 | head -3
strings /out/strata | grep -c 'STRATA_PF_MMVQ'
"
  echo "=== build end $(date +%F' '%T)"
  ls -l "$O/strata" 2>/dev/null; md5sum "$O/strata" 2>/dev/null
} >> "$LOG" 2>&1
grep -E "configure rc|test build rc|test run rc|ninja rc|build end" "$LOG" | tail -8
