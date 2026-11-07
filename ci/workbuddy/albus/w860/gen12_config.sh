#!/bin/bash
# W860-B3：用 Tensile 的**生成输入**（BenchmarkProblems/ForkParameters）为 gfx906 生成 f16 VALU kernel。
# 全程 --cpu-only --build-only：不占 GPU、不 benchmark、不碰生产。
set -u
SRC=/home/albus/strata166/rocm-libs
W859=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
TMP=/home/albus/strata166/tmp
LOG=/home/albus/strata166/data/w860_gen12.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== gen12 start $(date +%F" "%T)"
  docker run --rm --cpus=4 \
    -v "$SRC":/src:ro -v "$W859":/out -v "$W858":/g858 -v "$TMP":/in:ro "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
mkdir -p /out/work; cd /out/work
rm -rf /out/gen12; mkdir -p /out/gen12
echo "--- Tensile --cpu-only --build-only ---"
timeout 1500 python3 $TL/Tensile/bin/Tensile \
  --cpu-only --build-only --gpu-targets=gfx906 \
  --library-format=yaml \
  /in/gfx906_f16.yaml /out/gen12 2>&1 | tail -40
echo "--- 产物 ---"
find /out/gen12 -name "*.hsaco" -o -name "*.co" -o -name "TensileLibrary*" 2>/dev/null | head -10
find /out/gen12 -name "*.s" 2>/dev/null | head -4
'
  echo "=== gen12 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== gen12 start/,\$p" "$LOG" | tail -34
