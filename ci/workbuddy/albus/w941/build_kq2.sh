#!/bin/bash
# W941: build the standalone MMQ K-quant test (R61 driver) against the production build tree.
set -u
FLAGS="-DGGML_USE_HIP -DSTRATA_HIP_GFX906=1 -DSTRATA_MMQ_KQUANTS=1 -DSTRATA_MMQ_TQ=1 -DSTRATA_MMQ_TQP=1 -DSTRATA_Q6K_EXPERTS=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION=\"0.1.56\" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1"
INC="-I/out/ggml-tq-overlay -I/out/ggml-tq-overlay/include -I/llama.cpp/ggml/include -I/llama.cpp/ggml/src -I/llama.cpp/ggml/src/ggml-cuda -I/src/include -I/llama.cpp/ggml/src/../include -isystem /src/include/strata/platform/hip_compat"

hipcc $FLAGS -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 $INC \
  -c /src/tests/cuda/prefill_mmq_kquant_test.cpp -o /tmp/kq.o > /tmp/kq_build.log 2>&1
RC1=$?
echo "COMPILE_RC=$RC1"
[ $RC1 -ne 0 ] && tail -25 /tmp/kq_build.log && exit $RC1

hipcc --offload-arch=gfx906 /tmp/kq.o \
  /out/libstrata_mmq.a /out/libstrata_mmq_w4a4.a /out/ggml/src/libggml-base.a \
  -o /out/kq_pmc >> /tmp/kq_build.log 2>&1
RC2=$?
echo "LINK_RC=$RC2"
[ $RC2 -ne 0 ] && tail -30 /tmp/kq_build.log
ls -l /out/kq_pmc 2>/dev/null
