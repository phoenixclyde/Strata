#!/bin/bash
# W858-B 续 6：第三支 —— 关掉矩阵指令（gfx906 的 ISA 没有 MFMA），走非 MI 的 VALU 路径。
#   gfx942 的 logic 里 EnableMatrixInstruction: true + MatrixInstruction: [16,16,16,1]，
#   把它们改成 false / []，看生成器是否愿意为 gfx906 出 VALU kernel（Tensile 经典路径）。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b7.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B7 start $(date +%F" "%T)"
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/out/rocisa-install:/out/pylib:$TL
mkdir -p /out/logic906b /out/work
python3 - <<PYX
import io
LP = "/src/projects/hipblaslt/tensilelite/Tensile/Tests/unit/characterization/LibraryIO/data/logic_gfx942_HSS_BH.yaml"
lines = io.open(LP, encoding="utf-8").read().split("\n")
out = []
for ln in lines:
    t = ln.strip()
    if t.startswith("- gfx942"):        ln = ln.replace("gfx942", "gfx906")
    elif t == "- aquavanjaram":         ln = ln.replace("aquavanjaram", "vega20")
    elif t.startswith("EnableMatrixInstruction:"): ln = ln.split(":")[0] + ": false"
    elif t.startswith("MatrixInstruction:"):       ln = ln.split(":")[0] + ": []"
    out.append(ln)
io.open("/out/logic906b/logic_gfx906_nomi.yaml","w",encoding="utf-8").write("\n".join(out))
print("written; MI off")
PYX
cd /out/work
rm -rf /out/gen3; mkdir -p /out/gen3
timeout 1200 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906b /out/gen3 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 8 2>&1 | tail -40
echo "--- 尝试3 产物"
find /out/gen3 -type f | head -14
for f in $(find /out/gen3 -name "*.hsaco" -o -name "*.co" | head -2); do echo "== $f"; strings $f | grep -m3 -E "gfx906|amdhsa" ; done
'
  echo "=== B7 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== B7 start/,\$p" "$LOG" | tail -40
