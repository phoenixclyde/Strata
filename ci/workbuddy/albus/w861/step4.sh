#!/bin/bash
# W861-AA: --use-cache 复用 benchmark，跑到 LibraryLogic + GenerateLibrary
set -u
R=/home/albus/strata166
LOG=$R/data/w861_step4.log
: > "$LOG"
{
echo "=== step4 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=8 -v "$R/rocm-libs":/src -v "$R/data/w859_hblt":/out \
  -v "$R/data/w860_vega20":/v20 -v "$R/data/w858_hblt":/g858 \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out
echo "--- 完整流程 + use-cache（复用 gen16 的 1_ 2_）---"
nice -n 19 timeout 1500 python3 $TL/Tensile/bin/Tensile /v20/gfx906_f16_hand.yaml /out/gen16 \
  --use-cache --cpu-only --build-only --gpu-targets=gfx906 2>&1 | tail -25
echo "--- 阶段目录 ---"
ls /out/gen16
echo "--- LibraryLogic 产物 ---"
find /out/gen16 -maxdepth 2 -type d -name "3_*" -o -maxdepth 2 -type d -name "4_*" 2>/dev/null
find /out/gen16 -name "*.yaml" -newer /out/gen16/2_BenchmarkData 2>/dev/null | head -8
'
echo "=== step4 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== step4 start/,\$p" "$LOG" | tail -40
