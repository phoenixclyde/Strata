#!/bin/bash
# W861-AJ: 用自编 client 跑真 benchmark -> 3_LibraryLogic
set -u
R=/home/albus/strata166
LOG=$R/data/w861_bench.log
: > "$LOG"
{
echo "=== bench start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=8 --device /dev/kfd --device /dev/dri --group-add video \
  --ipc=host --security-opt seccomp=unconfined \
  -v "$R/rocm-libs":/src -v "$R/data/w859_hblt":/out -v "$R/data/w860_vega20":/v20 \
  -v "$R/data/w858_hblt":/g858 strata-gfx906:0.2.9-101 bash -lc '
set -u
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
CL=/out/build/tensilelite/client/tensilelite-client
echo "client: $CL"; ls -la $CL
cd /out
rm -rf /out/gen17
nice -n 19 timeout 2400 python3 $TL/Tensile/bin/Tensile /v20/gfx906_f16_hand.yaml /out/gen17 \
  --gpu-targets=gfx906 --prebuilt-client $CL 2>&1 | tail -30
echo "--- 阶段 ---"
ls /out/gen17 2>/dev/null
echo "--- LibraryLogic ---"
find /out/gen17 -maxdepth 2 -type d -name "3_*" 2>/dev/null
find /out/gen17 -name "*.yaml" -path "*3_*" 2>/dev/null | head -5
'
echo "=== bench end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== bench start/,\$p" "$LOG" | tail -40
