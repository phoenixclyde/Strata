#!/bin/bash
# R54: relink the engine with the patched verify.o and the megakernel object (inside the image).
# Usage: bash build_r54_img.sh   (mounts: /src = worktree, /build = a copy of gfx029-build)
set -eu
CXX=/opt/rocm/llvm/bin/clang++
AR=$(command -v llvm-ar || echo /opt/rocm/core-7.14/lib/llvm/bin/llvm-ar)
[ -x "$AR" ] || AR=ar
cd /build

echo "== 1 verify.cpp =="
$CXX -O3 -DNDEBUG -std=c++20 -Wall -Wextra \
  -DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_NATIVE_EXPERTS=1 -DSTRATA_VERIFY_MAX_T=8 \
  '-DSTRATA_VERSION="0.1.55"' -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 \
  -I/src/include -I/src/third_party/ggml/include -isystem /src/include/strata/platform/hip_compat -isystem /opt/rocm/include \
  -c /src/src/core/verify.cpp -o CMakeFiles/strata_engine.dir/src/core/verify.cpp.o 2> /tmp/verify.log
echo "verify rc=$? errors=$(grep -c 'error:' /tmp/verify.log || true)"

echo "== 2 megakernel_gdn.cu =="
$CXX -x hip -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -Wall -Wextra \
  -DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 \
  '-DSTRATA_VERSION="0.1.55"' -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1 \
  -DSTRATA_USE_HIP=1 \
  -I/src/third_party/ggml -I/src/include -isystem /src/include/strata/platform/hip_compat -isystem /opt/rocm/include \
  -c /src/src/kernels/cuda/megakernel_gdn.cu -o megakernel_gdn.cu.o 2> /tmp/mk.log
echo "megakernel rc=$? errors=$(grep -c 'error:' /tmp/mk.log || true)"

echo "== 3 archive =="
$AR r libstrata_engine.a CMakeFiles/strata_engine.dir/src/core/verify.cpp.o megakernel_gdn.cu.o
echo "archive rc=$? members=$($AR t libstrata_engine.a | grep -c 'megakernel_gdn.cu.o' || true)"

echo "== 4 link =="
ninja -t commands strata | tail -1 > /tmp/link_cmd.txt
wc -c < /tmp/link_cmd.txt
bash /tmp/link_cmd.txt 2> /tmp/link.log
echo "link rc=$?"
tail -3 /tmp/link.log
ls -l strata | awk '{print "bin_bytes="$5}'
./strata --version 2>&1 | head -2
