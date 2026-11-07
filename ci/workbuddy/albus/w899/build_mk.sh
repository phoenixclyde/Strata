#!/bin/bash
# R54: build the wave64 megakernel + the bitwise parity harness (worktree only).
set -u
cd /home/albus/strata166/work/r54 || exit 1
CXX=/opt/rocm/llvm/bin/clang++
FLAGS="-x hip -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -DSTRATA_USE_HIP=1 -DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1 -I./third_party/ggml -I./include -isystem ./include/strata/platform/hip_compat -isystem /opt/rocm/include"

$CXX $FLAGS -c src/kernels/cuda/megakernel_gdn.cu -o /tmp/mk64.o > /tmp/mk64.log 2>&1
rc=$?
echo "mk_rc=$rc errors=$(grep -c 'error:' /tmp/mk64.log)"
if [ "$rc" != 0 ]; then grep -m6 'error:' /tmp/mk64.log | cut -c1-180; exit 1; fi
stat -c 'obj_bytes=%s' /tmp/mk64.o

$CXX $FLAGS -c src/kernels/mk_gdn_parity.cpp -o /tmp/mkp64.o > /tmp/mkp64.log 2>&1
rc=$?
echo "parity_rc=$rc errors=$(grep -c 'error:' /tmp/mkp64.log)"
if [ "$rc" != 0 ]; then grep -m6 'error:' /tmp/mkp64.log | cut -c1-180; exit 1; fi

$CXX --hip-link --offload-arch=gfx906 /tmp/mkp64.o /tmp/mk64.o \
    -L/home/albus/strata166/gfx029-build -lstrata_kernels -lstrata_core \
    -L/opt/rocm/lib -lamdhip64 -o /tmp/mk_parity64 > /tmp/link64.log 2>&1
rc=$?
echo "link_rc=$rc"
if [ "$rc" != 0 ]; then
    echo "undefined=$(grep -c 'undefined reference' /tmp/link64.log)"
    grep -oE "undefined reference to .[^']*" /tmp/link64.log | sed 's/.*to .//' | sort -u | head -8
    exit 1
fi
stat -c 'bin_bytes=%s' /tmp/mk_parity64
