#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r77

echo "=== A. 手工编译 ngram.cpp（按 build.ninja 的 rule 逐字抄） ==="
docker run --rm -v $W:/src -v $B:/out -w /out strata-gfx906:0.2.9-101 bash -lc '
set -e
mkdir -p CMakeFiles/strata_kernels.dir/src/kernels
/opt/rocm/llvm/bin/clang++ \
  -DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION=\"0.1.55\" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 \
  -I/src/third_party/ggml -I/src/include -isystem /src/include/strata/platform/hip_compat -isystem /opt/rocm/include \
  -O3 -DNDEBUG -std=c++20 -Wall -Wextra \
  -MD -MT CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o \
  -MF CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o.d \
  -o CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o \
  -c /src/src/kernels/ngram.cpp 2>&1 | tail -20
echo "compile rc=$?"
ls -l CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o
echo "--- 新符号是否进对象 ---"
strings CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o | grep -c "this program may lock only"
' 2>&1 | tail -14

echo
echo "=== B. 归档进 libstrata_kernels.a ==="
docker run --rm -v $B:/out -w /out strata-gfx906:0.2.9-101 bash -lc '
cp libstrata_kernels.a libstrata_kernels.a.bak_w935
ar r libstrata_kernels.a CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o 2>&1 | tail -3
echo "rc=$?"
ls -l libstrata_kernels.a
' 2>&1 | tail -6
