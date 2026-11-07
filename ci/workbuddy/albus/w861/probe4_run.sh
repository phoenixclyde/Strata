#!/bin/bash
# W861-M: 编 probe4 并真跑 matmul（heuristic + 执行 + 数值校验）
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906b
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe4.log
: > "$LOG"
{
echo "=== probe4 start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /tmp
echo "--- compile ---"
hipcc -O2 -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>&1 | tail -8
ls -la /tmp/probe4 2>/dev/null || { echo COMPILE_FAILED; exit 1; }
echo "--- run (自编库 + 非 lazy 库) ---"
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
ldd /tmp/probe4 | grep -i hipblaslt
ls /v20/lib906
timeout 180 /tmp/probe4 - 256 512 256 2>&1
echo "rc=$?"
' 2>&1
echo "=== probe4 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe4 start/,\$p" "$LOG" | tail -45
