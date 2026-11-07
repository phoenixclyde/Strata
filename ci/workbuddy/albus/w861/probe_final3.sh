#!/bin/bash
# W861-P: 验符号 + 真跑 matmul
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906y
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_final3.log
: > "$LOG"
{
echo "=== final3 start $(date -u +%FT%TZ) ==="
L=$OUTD/build/library/libhipblaslt.so.1.4
echo "--- symbols ---"
echo -n "MessagePack defined: "; nm -D --defined-only $L 2>/dev/null | grep -c MessagePack
echo -n "LoadLibraryMapping: "; nm -D $L 2>/dev/null | grep -i LoadLibraryMapping | head -2
echo "--- run ---"
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
echo "--- probe3 (create only) ---"
cd /probe && timeout 90 ./probe3 2>&1 | grep -vE "LLVM option|Did you mean" | tail -8
echo "--- probe4 小 ---"
timeout 120 /tmp/probe4 - 64 64 64 2>&1 | grep -vE "LLVM option|Did you mean"
echo "--- probe4 生产形状 ---"
timeout 180 /tmp/probe4 - 256 5120 2560 2>&1 | grep -vE "LLVM option|Did you mean"
' 2>&1
echo "=== final3 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== final3 start/,\$p" "$LOG" | tail -45
