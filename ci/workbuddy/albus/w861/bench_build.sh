#!/bin/bash
# W861-D: 批量编 decode 分解所需微基准（纯 CPU，不动 strata 二进制）
set -u
R=/home/albus/strata166
LLM=$R/src028/third_party/llama.cpp
LOG=$R/data/w861_bench_build.log
: > "$LOG"
{
echo "=== bench build start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=8 \
  -v "$R/gfx029":/src -v "$R/gfx029-build":/out -v "$LLM":/llama.cpp:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out
nice -n 19 timeout 1500 cmake --build . -j 8 --target \
  b6_mmvq_bench q8_gemv_bench router_chain_bench native_expert_bench \
  native_mmvq_multi gdn_chunk_bench 2>&1 | tail -25
echo "--- binaries ---"
for b in b6_mmvq_bench q8_gemv_bench router_chain_bench native_expert_bench native_mmvq_multi gdn_chunk_bench; do
  if [ -x /out/$b ]; then echo "OK   $b  $(stat -c%s /out/$b)"; else echo "MISS $b"; fi
done
'
echo "=== bench build end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== bench build start/,\$p" "$LOG" | tail -35
