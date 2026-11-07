#!/bin/bash
# W861-D2: 逐个编 decode 分解所需 bench —— 一个 target 不存在不会拖垮全批
set -u
R=/home/albus/strata166
LLM=$R/src028/third_party/llama.cpp
LOG=$R/data/w861_bench_build2.log
: > "$LOG"
TL="b6_mmvq_bench q8_gemv_bench router_chain_bench native_expert_bench gdn_chunk_bench qsa_rows_bench gfx906_qsa_query_swizzle_probe mmq_expert_bench"
echo "=== bench build2 start $(date -u +%FT%TZ) ===" | tee -a "$LOG"
docker run --rm --cpus=10 \
  -v "$R/gfx029":/src -v "$R/gfx029-build":/out -v "$LLM":/llama.cpp:ro \
  -e TL="$TL" strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out
for t in $TL; do
  printf "%-36s " "$t"
  if nice -n 19 timeout 600 ninja "$t" -j 10 > /tmp/b_$t.log 2>&1; then
    sz=$(stat -c%s /out/$t 2>/dev/null || echo 0)
    echo "OK  $sz"
  else
    echo "FAIL: $(tail -2 /tmp/b_$t.log | tr "\n" " " | cut -c1-90)"
  fi
done
echo "--- final ---"
for t in $TL; do [ -x /out/$t ] && echo "OK   $t $(stat -c%s /out/$t)"; done
' 2>&1 | tee -a "$LOG"
echo "=== bench build2 end $(date -u +%FT%TZ) ===" | tee -a "$LOG"
