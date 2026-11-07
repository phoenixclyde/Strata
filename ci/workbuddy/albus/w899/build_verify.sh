#!/bin/bash
# R54: compile-check the patched verify.cpp TU with the build.ninja flags (worktree only).
set -u
cd /home/albus/strata166/work/r54 || exit 1
CXX=/opt/rocm/llvm/bin/clang++
DEF='-DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_NATIVE_EXPERTS=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION="0.1.55" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1'
INC='-I./include -I./third_party/ggml/include -isystem ./include/strata/platform/hip_compat -isystem /opt/rocm/include'
$CXX -O3 -DNDEBUG -std=c++20 -Wall -Wextra $DEF $INC -c src/core/verify.cpp -o /tmp/verify_r54.o > /tmp/verify_r54.log 2>&1
rc=$?
echo "verify_rc=$rc errors=$(grep -c 'error:' /tmp/verify_r54.log)"
grep -m8 'error:' /tmp/verify_r54.log | cut -c1-200
[ "$rc" = 0 ] && stat -c 'obj_bytes=%s' /tmp/verify_r54.o
exit $rc
