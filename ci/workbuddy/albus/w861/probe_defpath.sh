#!/bin/bash
# W861-AB: 把库放到 hipBLASLt 默认搜索路径，避免撞上 rocBLAS 目录里那份旧的
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906d
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_defpath.log
: > "$LOG"
{
echo "=== defpath start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib

echo "--- 1) 撞车验证：默认路径下的旧库是谁 ---"
ls -la /opt/rocm/lib/rocblas/library/gfx906/TensileLibrary_lazy_gfx906* 2>/dev/null

echo "--- 2) 把我们的库放进 hipblaslt 默认目录 ---"
D=/opt/rocm/lib/hipblaslt/library/gfx906
mkdir -p $D
cp -f /v20/lib906/* $D/
ls -la $D

echo "--- 3) 不带任何 libpath 跑（走默认路径）---"
unset HIPBLASLT_TENSILE_LIBPATH
timeout 180 /tmp/p4 - 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -20

echo "--- 4) 带 TENSILE_DB 看细节 ---"
TENSILE_DB=0xffff timeout 180 /tmp/p4 - 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | grep -E "Unknown key|solutions loaded|placeholder|algos=|Could not" | head -10
' 2>&1
echo "=== defpath end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== defpath start/,\$p" "$LOG" | tail -40
