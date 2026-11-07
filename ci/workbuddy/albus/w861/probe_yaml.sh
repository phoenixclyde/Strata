#!/bin/bash
# W861-O: 按 albus/w860/pack_lib.sh 的做法（YAML 库，不是 .dat）+ LAZY_LOAD=OFF 的库
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906y
CACHE=$(find $R/data/w859_hblt/gen16 -type d -path "*caches/*/source/library/gfx906" | head -1)
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_yaml.log
: > "$LOG"
{
echo "=== probe yaml start $(date -u +%FT%TZ) ==="
rm -rf "$LIB"; mkdir -p "$LIB"
# 照 pack_lib.sh：hsaco 去掉 xnack 后缀；库用 YAML。两种命名都摆，只改名字不改内容。
cp -f "$CACHE/Kernels.so-000-gfx906-xnack-.hsaco" "$LIB/Kernels.so-000-gfx906.hsaco"
cp -f "$CACHE/TensileLibrary.yaml" "$LIB/TensileLibrary_gfx906.yaml"
cp -f "$CACHE/TensileLibrary.yaml" "$LIB/TensileLibrary_lazy_gfx906.yaml"
cp -f "$CACHE/TensileLibrary.yaml" "$LIB/TensileLibrary_gfx906.dat" 2>/dev/null || true
ls -la "$LIB"
echo "--- yaml head ---"
head -6 "$LIB/TensileLibrary_gfx906.yaml"
echo "=== run probe4 (LAZY_LOAD=OFF 库 -> 找 TensileLibrary_gfx906.yaml) ==="
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
echo "--- files ---"; ls /v20/lib906
echo "--- create only ---"
cd /probe && (timeout 90 ./probe3 2>&1 | grep -vE "LLVM option|Did you mean" | tail -8) || true
echo "--- probe4 (heuristic + 真跑) ---"
timeout 120 /tmp/probe4 - 64 64 64 2>&1 | grep -vE "LLVM option|Did you mean"
echo "--- probe4 大形状 ---"
timeout 120 /tmp/probe4 - 256 2560 256 2>&1 | grep -vE "LLVM option|Did you mean"
' 2>&1
echo "=== probe yaml end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe yaml start/,\$p" "$LOG" | tail -50
