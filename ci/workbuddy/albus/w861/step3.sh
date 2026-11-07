#!/bin/bash
# W861-Z: 补跑 Tensile step 3（LibraryLogic）+ TCL 打包，得到运行时格式的库
set -u
R=/home/albus/strata166
SRC=$R/rocm-libs
OUTD=$R/data/w859_hblt
V20=$R/data/w860_vega20
W858=$R/data/w858_hblt
LOG=$R/data/w861_step3.log
: > "$LOG"
{
echo "=== step3 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=8 -v "$SRC":/src -v "$OUTD":/out -v "$V20":/v20 -v "$W858":/g858 \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
echo "--- gen16 现有阶段 ---"; ls /out/gen16
echo "--- 补跑 step 3 ---"
cd /out
nice -n 19 timeout 900 python3 $TL/Tensile/bin/Tensile /v20/gfx906_f16_hand.yaml /out/gen16c \
  --steps 3 --gpu-targets=gfx906 2>&1 | tail -20
echo "--- 产物 ---"
ls -R /out/gen16c 2>/dev/null | head -20
find /out/gen16c -name "*.yaml" -o -name "*.dat" 2>/dev/null | head -10
'
echo "=== step3 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== step3 start/,\$p" "$LOG" | tail -40
