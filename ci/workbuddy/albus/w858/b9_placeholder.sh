#!/bin/bash
# W858-B 收尾：生成 msgpack 库 → 用 HIPBLASLT_TENSILE_LIBPATH 指过去 → 看 algo 是否从 0 变 >0。
#   对照：不带 env（默认库）与带 env（我们的 gfx906 库）各跑一次。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b9.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B9 start $(date +%F" "%T)"
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
PIP="python3 -m pip install --no-cache-dir --timeout 90 --retries 6 -i https://mirrors.aliyun.com/pypi/simple"
echo "--- msgpack"
PYTHONPATH=/out/pylib python3 -c "import msgpack" 2>/dev/null || $PIP --target /out/pylib msgpack 2>&1 | tail -2
PYTHONPATH=/out/pylib python3 -c "import msgpack;print(\"msgpack\",msgpack.version)" 2>&1 | tail -1

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
print("logic head:", out[1].strip(), "|", out[2].strip())
PYX
cd /out/work
rm -rf /out/gen5; mkdir -p /out/gen5
timeout 1500 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906c /out/gen5 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=msgpack --no-enumerate -j 8 2>&1 | tail -14
echo "--- gen5 库文件"
ls -l /out/gen5/library/gfx906/ 2>/dev/null | head -10
find /out/gen5 -name "TensileLibrary*" -o -name "*.dat" | head -6

echo "--- 编探针"
cd /out
hiplink=""
cat > /out/probe_algos.cpp <<SRCEND
$(cat /dev/null)
SRCEND
' 2>&1
} >> "$LOG" 2>&1
echo "(占位)"
