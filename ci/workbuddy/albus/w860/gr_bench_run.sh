#!/bin/bash
# R21 零干扰验证：编 fused_gr_bench（只新增可执行文件，不动 strata 二进制），跑 v1 vs v3
set -u
R=/home/albus/strata166
LOG=$R/data/w860_gr_bench.log
: > "$LOG"
{
  echo "=== gr_bench start $(date +%F_%T) ==="
  docker run --rm --cpus=4 --device /dev/kfd --device /dev/dri --group-add video \
    -v "$R/gfx029":/src -v "$R/gfx029-build":/out strata-gfx906:0.2.9-101 bash -lc "
set -u
export PATH=/opt/rocm/bin:/$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:/${LD_LIBRARY_PATH:-}
cd /out
nice -n 19 timeout 900 cmake --build . --target fused_gr_bench -j 4 2>&1 | tail -10
echo '--- binary ---'; ls -l /out/fused_gr_bench 2>/dev/null || echo MISSING
if [ -x /out/fused_gr_bench ]; then
  echo '=== v1 (STRATA_GR_V3=0) ==='
  STRATA_GR_V3=0 /out/fused_gr_bench 300 1 8 2>&1 | tail -12
  echo '=== v3 (STRATA_GR_V3=1) ==='
  STRATA_GR_V3=1 /out/fused_gr_bench 300 1 8 2>&1 | tail -12
fi
"
  echo "=== gr_bench end $(date +%F_%T) rc=$? ==="
} >> "$LOG" 2>&1
sed -n "/=== gr_bench start/,\$p" "$LOG" | tail -40
