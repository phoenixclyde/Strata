#!/bin/bash
# R51: rebuild ONLY the Q4_K MMQ instance with the unpack hoisted, swap it into
# libstrata_mmq.a and relink the engine. Nothing else is recompiled; the pinned
# llama.cpp and the overlay in the build tree are untouched.
#
# mounts: /src = work/r55 (for hip_compat + strata includes), /build = copy of gfx029-build,
#         /llama = src028/third_party/llama.cpp, /ov = patched overlay, /work = helpers
set -eu
CXX=/opt/rocm/llvm/bin/clang++
AR=$(command -v llvm-ar || echo /opt/rocm/core-7.14/lib/llvm/bin/llvm-ar)
[ -x "$AR" ] || AR=ar
cd /build

echo "== 1 q4_K instance =="
$CXX -x hip -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 \
  -DGGML_USE_HIP -DSTRATA_HIP_GFX906=1 -DSTRATA_MMQ_KQUANTS=1 -DSTRATA_MMQ_TQ=1 -DSTRATA_MMQ_TQP=1 \
  -DSTRATA_VERIFY_MAX_T=8 '-DSTRATA_VERSION="0.1.55"' -DUSE_PROF_API=1 \
  -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1 \
  -I/ov -I/llama/ggml/include -I/llama/ggml/src -I/llama/ggml/src/ggml-cuda \
  -I/src/include -I/llama/ggml/src/../include \
  -isystem /src/include/strata/platform/hip_compat -isystem /opt/rocm/include \
  -c /ov/template-instances/mmq-instance-q4_k.cu \
  -o mmq-instance-q4_k.cu.o 2> /tmp/q4k.log
echo "compile rc=$? errors=$(grep -c 'error:' /tmp/q4k.log || true)"
grep -m5 'error:' /tmp/q4k.log | cut -c1-200 || true
ls -l mmq-instance-q4_k.cu.o | awk '{print "obj_bytes="$5}'

echo "== 2 swap the archive member =="
$AR r libstrata_mmq.a mmq-instance-q4_k.cu.o
echo "ar rc=$?"
$AR t libstrata_mmq.a | grep -c 'mmq-instance-q4_k.cu.o' | sed 's/^/members=/'

echo "== 3 link =="
ninja -t commands strata | tail -1 > /tmp/link_cmd.txt
wc -c < /tmp/link_cmd.txt | sed 's/^/link_cmd_bytes=/'
bash /tmp/link_cmd.txt 2> /tmp/link.log
echo "link rc=$?"
tail -3 /tmp/link.log
ls -l strata | awk '{print "bin_bytes="$5}'

echo "== 4 evidence that the hoist is in the code =="
/opt/rocm/llvm/bin/llvm-objdump -d --offload-arch=gfx906 strata 2>/dev/null \
  | grep -c 'v_dot4_i32_i8' | sed 's/^/total_dp4a_in_binary=/'
