#!/bin/bash
# W861-T: 无 LLVM 的自编库 + msgpack lazy 库 -> 探针（heuristic + 真跑）
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906      # 早先 make_lib.py 产出的 .dat + Mapping + hsaco
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_noyaml.log
: > "$LOG"
{
echo "=== probe noyaml start $(date -u +%FT%TZ) ==="
ls -la "$LIB" 2>/dev/null
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v /home/albus/strata166/data/w861_lib906b:/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
echo "--- lib in use ---"; ldd /tmp/probe4 | grep -i hipblaslt
echo "--- files ---"; ls /v20/lib906
echo "===== probe3 (create only) ====="
cd /probe && timeout 120 ./probe3 /v20/lib906 2>&1 | grep -viE "LLVM option|Did you mean" | head -12
echo "===== probe4 小形状 ====="
timeout 120 /tmp/probe4 /v20/lib906 64 64 64 2>&1 | grep -viE "LLVM option|Did you mean" | head -20
echo "===== probe4 生产形状 M=256 N=5120 K=2560 ====="
timeout 180 /tmp/probe4 /v20/lib906 256 5120 2560 2>&1 | grep -viE "LLVM option|Did you mean" | head -20
' 2>&1
echo "=== probe noyaml end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe noyaml start/,\$p" "$LOG" | tail -50
