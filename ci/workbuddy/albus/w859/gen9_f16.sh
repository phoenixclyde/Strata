#!/bin/bash
# W859-B：修 FMA_F16_HPA_MAD_MIX 的签名（gfx906 的 f16 MAC 组件），重生成 f16 logic 并探测
set -u
SRC=/home/albus/strata166/rocm-libs
W859=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w859_gen9.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== gen9 start $(date +%F" "%T)"
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$SRC":/src -v "$W859":/out -v "$W858":/g858 "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
F=$TL/Tensile/Components/MAC_F16_HPA.py
if ! grep -q W859sig $F; then
  sed -i "s/def __call__(self, writer, m, innerUnroll):/def __call__(self, writer, m, innerUnroll, *a, **kw):  # W859sig/" $F
  echo "  signature patched"
else
  echo "  already patched"
fi
grep -n "def __call__(self, writer, m" $F | head -2
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
cd /out/work
rm -rf /out/gen8; mkdir -p /out/gen8
timeout 600 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906h /out/gen8 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 6 2>&1 | tail -8
ls /out/gen8/library/gfx906 2>/dev/null | head -4
echo "=== probe ==="
LD_LIBRARY_PATH=/out/build/library:/opt/rocm/lib /g858/probe3 /out/gen8/library/gfx906 2>&1 | grep -viE "LLVM option|Did you mean" | tail -10
'
  echo "=== gen9 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== gen9 start/,\$p" "$LOG" | tail -22
