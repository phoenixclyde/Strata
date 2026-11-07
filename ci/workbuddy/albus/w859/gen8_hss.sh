#!/bin/bash
# W859-B：由 SB.yaml（非 MI 解）派生一份 gfx906 的 f16 logic，生成后探 f16 的 algo。
#   SB 的 problem type 是 SS（f32 in/out）；把 DataType 0 -> 4（f16）、开 HPA，解的参数不动。
set -u
SRC=/home/albus/strata166/rocm-libs
W859=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w859_gen8.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== gen8 start $(date +%F" "%T)"
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$SRC":/src:ro -v "$W859":/out -v "$W858":/g858 "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
mkdir -p /out/logic906h /out/work
python3 -m pip --version > /dev/null 2>&1
sed -e "s/^- navi31$/- vega20/" -e "s/^- gfx1100$/- gfx906/" \
    -e "0,/^  DataType: 0$/s//  DataType: 4/" \
    -e "0,/^  HighPrecisionAccumulate: false$/s//  HighPrecisionAccumulate: true/" \
    $TL/Tensile/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml > /out/logic906h/logic_gfx906_HSS.yaml
head -3 /out/logic906h/logic_gfx906_HSS.yaml
grep -m2 -E "^  DataType:|^  HighPrecisionAccumulate:" /out/logic906h/logic_gfx906_HSS.yaml
cd /out/work
rm -rf /out/gen8; mkdir -p /out/gen8
timeout 900 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906h /out/gen8 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 6 2>&1 | tail -8
ls /out/gen8/library/gfx906 2>/dev/null | head -6
echo "=== 探 f16 ==="
LD_LIBRARY_PATH=/out/build/library:/opt/rocm/lib /g858/probe3 /out/gen8/library/gfx906 2>&1 | grep -viE "LLVM option|Did you mean" | tail -10
'
  echo "=== gen8 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== gen8 start/,\$p" "$LOG" | tail -20
