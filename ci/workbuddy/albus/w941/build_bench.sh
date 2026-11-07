#!/bin/bash
# W941: build the production-shaped MMQ PMC driver.
set -u
FLAGS="-DGGML_USE_HIP -DSTRATA_HIP_GFX906=1 -DSTRATA_MMQ_KQUANTS=1 -DSTRATA_MMQ_TQ=1 -DSTRATA_MMQ_TQP=1 -DSTRATA_Q6K_EXPERTS=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION=\"0.1.56\" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1"
INC="-I/out/ggml-tq-overlay -I/out/ggml-tq-overlay/include -I/llama.cpp/ggml/include -I/llama.cpp/ggml/src -I/llama.cpp/ggml/src/ggml-cuda -I/src/include -I/llama.cpp/ggml/src/../include -isystem /src/include/strata/platform/hip_compat"

hipcc $FLAGS -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 $INC -c /work/kq_bench.cpp -o /tmp/kqb.o > /tmp/kqb.log 2>&1
echo "COMPILE_RC=$?"
tail -15 /tmp/kqb.log
[ -f /tmp/kqb.o ] || exit 1

hipcc --offload-arch=gfx906 /tmp/kqb.o /out/libstrata_mmq.a /out/libstrata_mmq_w4a4.a /out/ggml/src/libggml-base.a -o /out/kq_bench >> /tmp/kqb.log 2>&1
echo "LINK_RC=$?"
tail -15 /tmp/kqb.log
ls -l /out/kq_bench 2>/dev/null
