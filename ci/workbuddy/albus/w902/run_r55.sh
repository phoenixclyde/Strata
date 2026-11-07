#!/bin/bash
# R55 probe: link the top-k harness twice (baseline qsa_select vs ds_swizzle) and time both.
set -eu
CXX=/opt/rocm/llvm/bin/clang++
cd /build
INC="-I/src55/include -I/src55/third_party/ggml -isystem /src55/include/strata/platform/hip_compat -isystem /opt/rocm/include"
LIBS="-L/build -lstrata_kernels -lstrata_core -L/opt/rocm/lib -lamdhip64"

echo "== baseline link =="
$CXX -x hip -O2 -std=c++20 --offload-arch=gfx906 $INC /work/topk_bench.cpp -o /work/topk_base $LIBS 2>/work/base_link.log
echo "rc=$? errors=$(grep -c 'error:' /work/base_link.log || true)"
grep -m3 'error:' /work/base_link.log | cut -c1-160 || true

echo "== swap in the swizzle object =="
cp /work/qsa_select.r55.o /build/CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_select.cpp.o
ar r /build/libstrata_kernels.a /build/CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_select.cpp.o
echo "ar rc=$?"

echo "== swizzle link =="
$CXX -x hip -O2 -std=c++20 --offload-arch=gfx906 $INC /work/topk_bench.cpp -o /work/topk_swz $LIBS 2>/work/swz_link.log
echo "rc=$? errors=$(grep -c 'error:' /work/swz_link.log || true)"
grep -m3 'error:' /work/swz_link.log | cut -c1-160 || true

echo "== run (32K) =="
HSA_OVERRIDE_GFX_VERSION=9.0.6 /work/topk_base 32768 200 || true
HSA_OVERRIDE_GFX_VERSION=9.0.6 /work/topk_swz  32768 200 || true
echo "== run again (stability) =="
HSA_OVERRIDE_GFX_VERSION=9.0.6 /work/topk_base 32768 200 || true
HSA_OVERRIDE_GFX_VERSION=9.0.6 /work/topk_swz  32768 200 || true
