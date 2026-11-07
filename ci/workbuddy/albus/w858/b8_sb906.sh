#!/bin/bash
# W858-B 续 7：决定性一试 —— 用 gfx1100 的**非 MI** codegen 用例（SB.yaml）改成 gfx906/vega20，
# 看 TensileLite 能不能为本卡真正生成机器码。这是"能不能自建 hipBLASLt 表"的分水岭。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b8.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B8 start $(date +%F" "%T)"
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/out/rocisa-install:/out/pylib:$TL
mkdir -p /out/logic906c /out/work
python3 - <<PYX
import io
LP = "/src/projects/hipblaslt/tensilelite/Tensile/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml"
lines = io.open(LP, encoding="utf-8").read().split("\n")
out = []
for ln in lines:
    t = ln.strip()
    if t == "- navi31":   ln = "- vega20"
    elif t == "- gfx1100": ln = "- gfx906"
    out.append(ln)
io.open("/out/logic906c/logic_gfx906_SB.yaml","w",encoding="utf-8").write("\n".join(out))
print("head:", out[1].strip(), "|", out[2].strip())
PYX
cd /out/work
rm -rf /out/gen4; mkdir -p /out/gen4
timeout 1500 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906c /out/gen4 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 8 2>&1 | tail -30
echo "--- 尝试4 产物"
find /out/gen4 -type f | head -14
for f in $(find /out/gen4 -name "*.hsaco" -o -name "*.co" | head -3); do echo "== $f"; ls -l $f; strings $f | grep -m3 -E "gfx906|amdhsa" ; done
'
  echo "=== B8 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== B8 start/,\$p" "$LOG" | tail -34
