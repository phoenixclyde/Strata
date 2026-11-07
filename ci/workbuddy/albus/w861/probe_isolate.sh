#!/bin/bash
# W861-AC: 移开 rocBLAS 目录里那份同名旧库，再跑
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906d
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_isolate.log
: > "$LOG"
{
echo "=== isolate start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib

echo "--- 移开 rocBLAS 目录里的同名库 ---"
for f in /opt/rocm/lib/rocblas/library/gfx906/TensileLibrary_lazy_gfx906*; do
  [ -e "$f" ] && mv "$f" "$f.w861bak" && echo "moved $f"
done

echo "--- 跑 probe4（显式 libpath）---"
timeout 180 /tmp/p4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -20

echo "--- 仍失败就看 DB ---"
TENSILE_DB=0xffff timeout 180 /tmp/p4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" \
  | grep -E "Unknown key|Error loading|solutions loaded|placeholder|Could not|algos=" | head -10
' 2>&1
echo "=== isolate end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== isolate start/,\$p" "$LOG" | tail -40
