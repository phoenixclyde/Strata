#!/bin/bash
# W861-C: 绕过 cmake regenerate，直接用已生成的 build.ninja 编 fused_gr_bench（纯 CPU）
set -u
R=/home/albus/strata166
LOG=$R/data/w861_gr_build.log
: > "$LOG"
{
echo "=== gr build start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=8 -v "$R/gfx029":/src -v "$R/gfx029-build":/out strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out
echo "--- targets with fused_gr ---"
ninja -t targets all 2>/dev/null | grep -c fused_gr_bench
echo "--- touch build.ninja to skip RERUN_CMAKE ---"
touch /out/build.ninja
echo "--- build ---"
nice -n 19 timeout 900 ninja fused_gr_bench -j 8 2>&1 | tail -25
echo "--- binary ---"
ls -l /out/fused_gr_bench 2>/dev/null || echo MISSING
'
echo "=== gr build end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== gr build start/,\$p" "$LOG" | tail -40
