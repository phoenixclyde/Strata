#!/bin/bash
# W861-W: compute 16F vs 32F 对照（判定 algos=0 是否 compute type 造成）
set -u
R=/home/albus/strata166
LOG=$R/data/w861_probe5.log
: > "$LOG"
{
echo "=== probe5 start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$R/data/w861_lib906d":/v20/lib906:ro -v "$R/data/w859_hblt/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro -v /home/albus/w861_probe5.cpp:/p5.cpp:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
hipcc -O2 -std=c++17 /p5.cpp -o /tmp/p5 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
export HIPBLASLT_LOG_LEVEL=3
echo "===== compute 32F (HHS) ====="
timeout 120 /tmp/p4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -10
echo "===== compute 16F (HHH) ====="
timeout 120 /tmp/p5 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -10
echo "===== 小数形状 compute 16F M=128 N=128 K=128 ====="
timeout 120 /tmp/p5 /v20/lib906 128 128 128 2>&1 | grep -viE "LLVM option|Did you mean" | head -10
' 2>&1
echo "=== probe5 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe5 start/,\$p" "$LOG" | tail -35
