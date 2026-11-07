#!/bin/bash
set -u
B=/home/albus/strata166/gfx029-build
W=/home/albus/strata166/work/r77

echo "=== 备份当前产物 ==="
ls -l $B/strata | awk '{print $5, $6, $7, $8}'
md5sum $B/strata
cp -f $B/strata $B/strata.bak-8e92c662 2>/dev/null && echo "backup ok"

echo
echo "=== A. 编译 generate.cpp（work/r77 = 主线 + 5a13c34f + e1b27d54） ==="
docker run --rm -v $W:/src -v $B:/out -w /out strata-gfx906:0.2.9-101 bash -lc '
set -e
/opt/rocm/llvm/bin/clang++ -DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_NATIVE_EXPERTS=1 -DSTRATA_PREFILL_FUSED=1 -DSTRATA_PREFILL_MMQ=1 -DSTRATA_ROCBLAS_AVAILABLE=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION=\"0.1.55\" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -I/src/include -I/src/third_party/ggml/include -isystem /src/include/strata/platform/hip_compat -isystem /opt/rocm/include -O3 -DNDEBUG -std=c++20 -Wall -Wextra -MD -MT CMakeFiles/strata.dir/src/program/generate.cpp.o -MF CMakeFiles/strata.dir/src/program/generate.cpp.o.d -o CMakeFiles/strata.dir/src/program/generate.cpp.o -c /src/src/program/generate.cpp 2>&1 | grep -E "error|Error" | head -20
echo "COMPILE_DONE"
ls -l CMakeFiles/strata.dir/src/program/generate.cpp.o | awk "{print \$5}"
echo "--- 新字符串是否进对象 ---"
strings CMakeFiles/strata.dir/src/program/generate.cpp.o | grep -c "fatal GPU error"
strings CMakeFiles/strata.dir/src/program/generate.cpp.o | grep -c "STRATA_INJECT_FATAL"
' 2>&1 | tail -12

echo
echo "=== B. 链接 ==="
docker run --rm -v $B:/out -w /out strata-gfx906:0.2.9-101 bash -lc '
set -e
cd /out
/opt/rocm/lib/llvm/bin/clang++ -O3 -DNDEBUG --offload-arch=gfx906 CMakeFiles/strata.dir/src/program/generate.cpp.o -o strata libstrata_engine.a libstrata_prefill.a libstrata_spec.a libstrata_engine.a libstrata_kernels.a libstrata_core.a libstrata_kernels_cpu.a ggml/src/libggml-cpu.a /opt/rocm/lib/libhipblas.so.3.7 /opt/rocm/lib/librocblas.so.5.7 libstrata_mmq.a libstrata_mmq_w4a4.a /opt/rocm/lib/libamdhip64.so.7.16.26323-0000000 /opt/rocm/lib/llvm/lib/clang/24/lib/linux/libclang_rt.builtins-x86_64.a /opt/rocm/lib/libamdhip64.so.7.16.26323-0000000 ggml/src/libggml-base.a -lm 2>&1 | tail -8
echo "LINK_DONE"
' 2>&1 | tail -6

echo
echo "=== C. 产物验证 ==="
ls -l $B/strata | awk '{print $5}'
md5sum $B/strata
echo "--- 期望有：fatal GPU error / STRATA_INJECT_FATAL / PLE 提限 ---"
strings $B/strata | grep -c "fatal GPU error"
strings $B/strata | grep -c "STRATA_INJECT_FATAL"
strings $B/strata | grep -c "this program may lock only"
echo "--- 期望为 0：R66/R68 ---"
strings $B/strata | grep -c "STRATA_PF_GROUP_SCRATCH"
strings $B/strata | grep -c "STRATA_PREFILL_ROUTED_STREAM"
strings $B/strata | grep -c "STRATA_PF_HC_REGION"
strings $B/strata | grep -c "STRATA_SERVE_STOP_BOUND"
