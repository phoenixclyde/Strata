#!/bin/bash
# W861-F2: 重跑 b6 并存全量（不 tail），同时跑 qsa_rows_bench
set -u
R=/home/albus/strata166
LOG=$R/data/w861_b6_full.log
: > "$LOG"
{
echo "=== b6 full start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$R/gfx029-build":/out strata-gfx906:0.2.9-101 bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out
echo "===== b6 FULL ====="
timeout 300 ./b6_mmvq_bench 100 0 1 2>&1
echo "rc=$?"
if [ -x /out/qsa_rows_bench ]; then
  echo "===== qsa_rows_bench ====="
  timeout 180 ./qsa_rows_bench 2>&1 | head -40
fi
if [ -x /out/native_expert_bench ]; then
  echo "--- native_expert_bench usage ---"
  timeout 60 ./native_expert_bench 2>&1 | head -12
fi
' 2>&1
echo "=== b6 full end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
wc -l "$LOG"
