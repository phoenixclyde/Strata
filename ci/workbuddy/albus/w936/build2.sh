#!/bin/bash
set -u
B=/home/albus/strata166/gfx029-build
W=/home/albus/strata166/work/r77

echo "=== 补丁是否真在树里 ==="
grep -c "exit_if_gpu_fatal" $W/src/program/generate.cpp
grep -n "fatal GPU error" $W/src/program/generate.cpp | head -3

echo
echo "=== 重新编译，完整错误输出 ==="
docker run --rm -v $W:/src -v $B:/out -w /out strata-gfx906:0.2.9-101 bash -lc '
/opt/rocm/llvm/bin/clang++ -DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_NATIVE_EXPERTS=1 -DSTRATA_PREFILL_FUSED=1 -DSTRATA_PREFILL_MMQ=1 -DSTRATA_ROCBLAS_AVAILABLE=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION=\"0.1.55\" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -I/src/include -I/src/third_party/ggml/include -isystem /src/include/strata/platform/hip_compat -isystem /opt/rocm/include -O3 -DNDEBUG -std=c++20 -Wall -Wextra -MD -MT CMakeFiles/strata.dir/src/program/generate.cpp.o -MF CMakeFiles/strata.dir/src/program/generate.cpp.o.d -o CMakeFiles/strata.dir/src/program/generate.cpp.o -c /src/src/program/generate.cpp > /tmp/cc.log 2>&1
echo "CC_RC=$?"
grep -E "error:" /tmp/cc.log | head -15
echo "--- 错误数 ---"
grep -c "error:" /tmp/cc.log
ls -l CMakeFiles/strata.dir/src/program/generate.cpp.o | awk "{print \$5}"
strings CMakeFiles/strata.dir/src/program/generate.cpp.o | grep -c "fatal GPU error"
' 2>&1 | tail -25
