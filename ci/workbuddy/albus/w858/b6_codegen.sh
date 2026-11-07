#!/bin/bash
# W858-B 续 5：gfx906 codegen 的两支尝试（rocisa 已编好在 /out/rocisa-install）
#   尝试 1：拿 gfx942 的 logic，命令行 --architecture=gfx906 → 看它是拒绝还是降级
#   尝试 2：把 logic 的 arch 行改成 gfx906/vega20 再跑（= 手工造一份 vega20 logic 的最小实验）
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b6.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B6 start $(date +%F" "%T)"
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
SLOG=$TL/Tensile/Tests/unit/characterization/LibraryIO/data/logic_gfx942_HSS_BH.yaml
export PYTHONPATH=/out/rocisa-install:/out/pylib:$TL
mkdir -p /out/logic942 /out/logic906 /out/work

echo "############ 尝试 1：原样 logic(942) + --architecture=gfx906"
cp $SLOG /out/logic942/
rm -rf /out/gen1; mkdir -p /out/gen1
cd /out/work
timeout 900 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic942 /out/gen1 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 8 2>&1 | tail -18
echo "--- 尝试1 产物"; find /out/gen1 -type f | head -8

echo
echo "############ 尝试 2：把 logic 的 arch 改成 gfx906 / vega20"
python3 - <<PYX
import io
LP = "/src/projects/hipblaslt/tensilelite/Tensile/Tests/unit/characterization/LibraryIO/data/logic_gfx942_HSS_BH.yaml"
s = io.open(LP, encoding="utf-8").read().split("\n")
print("orig head:", s[1].strip(), "|", s[2].strip())
s[1] = "- vega20"
s[2] = "- gfx906"
io.open("/out/logic906/logic_gfx906_HSS_BH.yaml","w",encoding="utf-8").write("\n".join(s))
print("new  head:", s[1].strip(), "|", s[2].strip())
PYX
rm -rf /out/gen2; mkdir -p /out/gen2
cd /out/work
timeout 900 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906 /out/gen2 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 8 2>&1 | tail -40
echo "--- 尝试2 产物"; find /out/gen2 -type f | head -10
for f in $(find /out/gen2 -name "*.hsaco" -o -name "*.co" | head -2); do echo "== $f"; strings $f | grep -m3 -E "gfx906|amdhsa" ; done
'
  echo "=== B6 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/############/,\$p" "$LOG" | tail -50
