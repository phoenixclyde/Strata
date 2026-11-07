#!/bin/bash
# W824: 用与生产完全相同的 CMake 选项构建上游 0.2.7.1（engine 0.1.53）。
# 用法: w824_build.sh [jobs]
set -u
S=/home/albus/strata166/src0271
O=/home/albus/strata166/src0271_out
J=${1:-10}
LOG=/home/albus/strata166/data/w824_build.log
mkdir -p "$O"
: > "$LOG"

{
  echo "=== build start $(date +%F' '%T)  jobs=$J"
  docker run --rm --name strata-w824build -v "$S":/src -v "$O":/out strata-gfx906:0.2.4p4 bash -lc "
set -u
cd /src
cmake -S . -B build-0271 -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_ENABLE_CUDA=ON -DSTRATA_ENABLE_HIP=OFF -DSTRATA_ENABLE_SYCL=OFF \
  -DSTRATA_GGML_DIR=/src/third_party/llama.cpp \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_DSV41=OFF \
  -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_PREFILL_MMQ=OFF \
  -DSTRATA_Q6K_EXPERTS=OFF -DSTRATA_WERROR=OFF
rc=\$?
echo \"--- configure rc=\$rc\"
[ \$rc -ne 0 ] && exit \$rc
nice -n 15 ninja -C build-0271 -j $J strata
rc=\$?
echo \"--- ninja rc=\$rc\"
[ \$rc -ne 0 ] && exit \$rc
cp build-0271/strata /out/strata-0.1.53
/out/strata-0.1.53 --version
"
  echo "=== build end $(date +%F' '%T) rc=$?"
  ls -la "$O"
} >> "$LOG" 2>&1
