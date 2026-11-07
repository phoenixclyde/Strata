#!/bin/bash
# R51 diagnosis: why is the hoisted Q4_K MMQ 2.13x SLOWER?
# Compiles the same instance TU twice (baseline vs hoisted) and reports the
# per-kernel resource usage, which is where a register spill would show up.
set -u
CXX=/opt/rocm/llvm/bin/clang++
FLAGS="-x hip -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906
  -DGGML_USE_HIP -DSTRATA_HIP_GFX906=1 -DSTRATA_MMQ_KQUANTS=1 -DSTRATA_MMQ_TQ=1 -DSTRATA_MMQ_TQP=1
  -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION=\"0.1.55\" -DUSE_PROF_API=1
  -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1
  -I/llama/ggml/include -I/llama/ggml/src -I/llama/ggml/src/ggml-cuda
  -I/src/include -isystem /src/include/strata/platform/hip_compat -isystem /opt/rocm/include
  -Rpass-analysis=kernel-resource-usage"

echo "===== baseline (pinned) ====="
$CXX $FLAGS -c /llama/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu \
    -o /tmp/base.o 2> /tmp/base.log
echo "rc=$? errors=$(grep -c 'error:' /tmp/base.log || true)"
grep -oE 'NumVgprs: [0-9]+.*SpillSize: [0-9]+' /tmp/base.log | sort | uniq -c | sort -rn | head -6
grep -oE 'SpillSize: [0-9]+' /tmp/base.log | sort | uniq -c | head -6

echo "===== hoisted ====="
$CXX $FLAGS -c /ov/template-instances/mmq-instance-q4_k.cu -o /tmp/hoist.o 2> /tmp/hoist.log
echo "rc=$? errors=$(grep -c 'error:' /tmp/hoist.log || true)"
grep -oE 'NumVgprs: [0-9]+.*SpillSize: [0-9]+' /tmp/hoist.log | sort | uniq -c | sort -rn | head -6
grep -oE 'SpillSize: [0-9]+' /tmp/hoist.log | sort | uniq -c | head -6

echo "===== object sizes ====="
ls -l /tmp/base.o /tmp/hoist.o | awk '{print $5, $9}'
