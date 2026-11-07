#!/bin/bash
# W861-V2: predicate 放宽对照实验（从 yaml 读、写 lazy 库）
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906d
CACHE=$(find $R/data/w859_hblt/gen16 -type d -path "*caches/*/source/library/gfx906" | head -1)
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_relax2.log
: > "$LOG"
{
echo "=== relax2 start $(date -u +%FT%TZ) ==="
rm -rf "$LIB"; mkdir -p "$LIB"
docker run --rm -v "$R/rocm-libs":/src:ro -v "$CACHE":"$CACHE":ro -v "$LIB":/out \
  -v /home/albus/rx4.py:/rx.py:ro -v "$R/data/w858_hblt":/g858:ro \
  strata-gfx906:0.2.9-101 bash -lc "
set -u
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:/src/projects/hipblaslt/tensilelite
python3 /rx.py '$CACHE' /out
"
echo "--- probe ---"
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
echo "===== probe3 ====="
cd /probe && timeout 120 ./probe3 /v20/lib906 2>&1 | grep -viE "LLVM option|Did you mean" | head -12
echo "===== probe4 生产形状 ====="
timeout 180 /tmp/probe4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -18
' 2>&1
echo "=== relax2 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== relax2 start/,\$p" "$LOG" | tail -45
