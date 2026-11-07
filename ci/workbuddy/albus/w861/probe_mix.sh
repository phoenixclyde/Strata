#!/bin/bash
# W861-X: LAZY_LOAD=OFF 的库 + lazy 命名的库文件（绕开 initLibraryMapping 的前缀硬检查）
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906d
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_mix.log
: > "$LOG"
{
echo "=== mix start $(date -u +%FT%TZ) ==="
echo "--- 重编 LAZY_LOAD=OFF ---"
sed -i 's|-DHIPBLASLT_ENABLE_LAZY_LOAD=ON|-DHIPBLASLT_ENABLE_LAZY_LOAD=OFF|' /home/albus/w861_noyaml_build2.sh
bash /home/albus/w861_noyaml_build2.sh 2>&1 | tail -4
echo "--- 现有库文件 ---"
ls -la "$LIB"
echo "--- probe ---"
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
echo "===== probe3 ====="
cd /probe && timeout 120 ./probe3 /v20/lib906 2>&1 | grep -viE "LLVM option|Did you mean" | head -14
echo "===== probe4 生产形状 ====="
timeout 180 /tmp/p4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -18
' 2>&1
echo "=== mix end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== mix start/,\$p" "$LOG" | tail -40
