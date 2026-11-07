#!/bin/bash
# W860-B4：用 **rocBLAS 原生的 vega20 HHS_BH logic**（gfx906 + f16 + f32 累加）生成 hipBLASLt 能吃的库。
# 全程 CPU-only，限 4 核。
set -u
SRC=/home/albus/strata166/rocm-libs
OUTD=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
V20=/home/albus/strata166/data/w860_vega20
LOG=/home/albus/strata166/data/w860_gen13.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== gen13 start $(date +%F" "%T)"
  docker run --rm --cpus=4 \
    -v "$SRC":/src:ro -v "$OUTD":/out -v "$W858":/g858 -v "$V20":/v20:ro "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
mkdir -p /out/work; cd /out/work
rm -rf /out/gen13; mkdir -p /out/gen13
echo "--- logic 文件 ---"; ls -l /v20/logic
echo "--- TensileCreateLibrary ---"
nice -n 19 timeout 1800 python3 $TL/Tensile/bin/TensileCreateLibrary /v20/logic /out/gen13 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 3 2>&1 | tail -20
echo "--- 产物 ---"
ls -l /out/gen13/library/gfx906 2>/dev/null | head -8
for f in /out/gen13/library/gfx906/*.hsaco; do [ -e "$f" ] && strings "$f" | grep -m1 amdhsa.target; done
'
  echo "=== gen13 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== gen13 start/,\$p" "$LOG" | tail -28
