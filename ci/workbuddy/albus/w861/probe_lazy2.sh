#!/bin/bash
# W861-U: LAZY_LOAD=ON 的库 + mapping 指回主库 -> 探针
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906c
CACHE=$(find $R/data/w859_hblt/gen16 -type d -path "*caches/*/source/library/gfx906" | head -1)
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_lazy2.log
: > "$LOG"
{
echo "=== lazy2 start $(date -u +%FT%TZ) ==="
echo "--- 1) 重编 LAZY_LOAD=ON ---"
sed -i 's|-DHIPBLASLT_ENABLE_LAZY_LOAD=OFF|-DHIPBLASLT_ENABLE_LAZY_LOAD=ON|' /home/albus/w861_noyaml_build2.sh
bash /home/albus/w861_noyaml_build2.sh 2>&1 | tail -4
echo "--- 2) 造 lazy 库 ---"
rm -rf "$LIB"; mkdir -p "$LIB"
docker run --rm -v "$R/rocm-libs":/src:ro -v "$CACHE":"$CACHE":ro -v "$LIB":/out \
  -v /home/albus/w861_make_lib3.py:/mk3.py:ro -v "$R/data/w858_hblt":/g858:ro \
  strata-gfx906:0.2.9-101 bash -lc "
set -u
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:/src/projects/hipblaslt/tensilelite
python3 /mk3.py '$CACHE' /out
"
echo "--- 3) 探针 ---"
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
ls /v20/lib906
echo "===== probe3 ====="
cd /probe && timeout 120 ./probe3 /v20/lib906 2>&1 | grep -viE "LLVM option|Did you mean" | head -12
echo "===== probe4 小 ====="
timeout 120 /tmp/probe4 /v20/lib906 64 64 64 2>&1 | grep -viE "LLVM option|Did you mean" | head -18
echo "===== probe4 生产形状 ====="
timeout 180 /tmp/probe4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -18
' 2>&1
echo "=== lazy2 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== lazy2 start/,\$p" "$LOG" | tail -50
