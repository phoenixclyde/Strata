#!/bin/bash
# W861-F: 跑 decode dense 侧微基准（GPU 只占几秒；生产 GPU 空闲 0%）
set -u
R=/home/albus/strata166
LOG=$R/data/w861_b6_run.log
: > "$LOG"
{
echo "=== b6 run start $(date -u +%FT%TZ) ==="
echo "--- vram before ---"; cat /sys/class/drm/card0/device/mem_info_vram_used 2>/dev/null
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$R/gfx029-build":/out strata-gfx906:0.2.9-101 bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out
echo "===== b6_mmvq_bench (dense 投影, decode 形状) ====="
timeout 300 ./b6_mmvq_bench 100 0 1 2>&1 | tail -60
echo "rc=$?"
echo "===== router_chain_bench (T=2) ====="
timeout 180 ./router_chain_bench 2 20 2>&1 | tail -25
echo "rc=$?"
' 2>&1
echo "--- vram after ---"; cat /sys/class/drm/card0/device/mem_info_vram_used 2>/dev/null
echo "=== b6 run end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== b6 run start/,\$p" "$LOG" | tail -80
