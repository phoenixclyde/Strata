#!/bin/bash
# W856 · hipBLASLt 支线 P0 第三轮：把 rocisa 装好，跑真 codegen
set -u
SRC=/home/albus/strata166/rocm-libs
IMG=strata-gfx906:0.2.9-101
OUT=/home/albus/strata166/data/w856_hblt_p0
LOG=$OUT/p0c_$(date +%H%M%S).log
mkdir -p "$OUT"; : > "$LOG"
exec > >(tee -a "$LOG") 2>&1
hl(){ printf '\n== %s\n' "$1"; }

hl "1 组装 rocisa（源码包 + 镜像里的原生扩展）"
docker run --rm --entrypoint bash -v "$SRC":/src:ro -v "$OUT":/out "$IMG" -lc '
set -u
PY=/out/pylib
mkdir -p $PY
rm -rf $PY/rocisa
cp -r /src/projects/hipblaslt/tensilelite/rocisa/rocisa $PY/rocisa
cp /opt/rocm/share/hipblaslt/tensilelite/rocisa/_rocisa.abi3.so $PY/rocisa/ 2>/dev/null
cp /opt/rocm/share/hipblaslt/tensilelite/rocisa/libstinkytofu.so* $PY/rocisa/ 2>/dev/null
ls $PY/rocisa | head -8
export PYTHONPATH=$PY:/src/projects/hipblaslt/tensilelite
python3 -c "import rocisa;print(\"rocisa OK\", rocisa.__file__)" 2>&1 | tail -3
' 2>&1 | tail -14

hl "2 gfx906 的 ISA 能力（不管 codegen 成不成，这条都值钱）"
docker run --rm --entrypoint bash -v "$SRC":/src:ro -v "$OUT":/out "$IMG" -lc '
set -u
export PYTHONPATH=/out/pylib:/src/projects/hipblaslt/tensilelite
python3 - <<PY 2>&1 | tail -20
import rocisa
from rocisa import rocIsa
for arch in ("gfx906","gfx1100","gfx90a"):
    try:
        isa = rocIsa.getInstance()
        isa.setKernel(isa.getKernel(arch, "f16", 2, 2))
        print(arch, "MFMA=", isa.isMFMA(), "WMMA=", getattr(isa,"isWMMA",lambda:None)())
    except Exception as e:
        print(arch, "FAIL", type(e).__name__, str(e)[:120])
PY
' 2>&1 | tail -10

hl "3 codegen（gfx906）"
docker run --rm --entrypoint bash -v "$SRC":/src:ro -v "$OUT":/out "$IMG" -lc '
set -u
export PYTHONPATH=/out/pylib:/src/projects/hipblaslt/tensilelite
cd /src/projects/hipblaslt/tensilelite
mkdir -p /out/gen
Y=/src/projects/hipblaslt/tensilelite/tensilelite/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml
for i in $(seq 1 8); do
  echo "--- attempt $i ---"
  out=$(python3 tensilelite/bin/TensileCreateLibrary --architecture=gfx906 --logic=$Y \
        --output-path=/out/gen --code-object-version=5 --library-format=yaml 2>&1)
  echo "$out" | tail -14
  mod=$(echo "$out" | grep -o "No module named '"'"'[^'"'"']*'"'"'" | head -1 | sed "s/No module named '"'"'//;s/'"'"'//;s/\..*//")
  if [ -n "$mod" ]; then
    echo "  -> pip install $mod"
    python3 -m pip install --target /out/pylib --no-cache-dir -q "$mod" 2>&1 | tail -2
    continue
  fi
  break
done
echo "--- 产物 ---"
find /out/gen -type f 2>/dev/null | head -15
' 2>&1 | tail -45

hl "4 判定"
if grep -qiE "requires gfx90a\+|amdhsa_accum_offset|unknown directive" "$LOG"; then
  echo "WALL —— 汇编阶段撞 gfx90a+ 指令"
elif find "$OUT/gen" \( -name '*.hsaco' -o -name '*.co' \) 2>/dev/null | grep -q .; then
  echo "PASS —— 有 .hsaco"
elif find "$OUT/gen" -name '*.s' 2>/dev/null | grep -q .; then
  echo "PARTIAL —— 有 .s 未汇编"
else
  echo "BLOCK —— 无产物"
fi
echo "日志: $LOG"
