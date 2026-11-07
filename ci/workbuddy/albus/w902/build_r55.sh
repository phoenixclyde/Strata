#!/bin/bash
# R55: compile qsa_select.cu twice (baseline vs ds_swizzle) and report the ISA mix.
set -eu
CXX=/opt/rocm/llvm/bin/clang++
DEF='-DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION="0.1.55" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1'
FLAGS='-x hip -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -Wall -Wextra'

build() {   # $1 = source tree, $2 = tag
    local SRC=$1 TAG=$2
    local INC="-I$SRC/third_party/ggml -I$SRC/include -isystem $SRC/include/strata/platform/hip_compat -isystem /opt/rocm/include"
    $CXX $FLAGS $DEF $INC -c $SRC/src/kernels/cuda/qsa_select.cu -o /work/qsa_select.$TAG.o 2> /work/$TAG.log
    echo "$TAG compile rc=$? errors=$(grep -c 'error:' /work/$TAG.log || true)"
    $CXX $FLAGS $DEF $INC --cuda-device-only -S $SRC/src/kernels/cuda/qsa_select.cu -o /work/$TAG.s 2>> /work/$TAG.log || true
    echo "$TAG ds_bpermute=$(grep -c ds_bpermute /work/$TAG.s || true) ds_swizzle=$(grep -c ds_swizzle /work/$TAG.s || true) v_mov_dpp=$(grep -c v_mov_dpp /work/$TAG.s || true)"
}

build /src54 base
build /src55 r55
