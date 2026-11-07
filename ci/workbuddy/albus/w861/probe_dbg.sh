#!/bin/bash
# W861-Y: TENSILE_DB 全开，看库加载了几个解、heuristic 筛在哪
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906d
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_dbg.log
: > "$LOG"
{
echo "=== dbg start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
echo "--- files ---"; ls /v20/lib906
echo "===== TENSILE_DB=0xffff ====="
TENSILE_DB=0xffff timeout 120 /tmp/p4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -40
' 2>&1
echo "=== dbg end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== dbg start/,\$p" "$LOG" | tail -45
