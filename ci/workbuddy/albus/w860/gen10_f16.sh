#!/bin/bash
# W860-B：把 FMA_F16_HPA_MAD_MIX 对齐到新 Component API（对照同文件 DOT2 的 5 参签名），
#          再为 gfx906 生成 f16 非 MI 库。全程 CPU-only（不给 --device），限 4 核 + nice 19。
set -u
SRC=/home/albus/strata166/rocm-libs
W859=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w860_gen10.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== gen10 start $(date +%F" "%T)"
  docker run --rm --cpus=4 \
    -v "$SRC":/src -v "$W859":/out -v "$W858":/g858 "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
F=$TL/Tensile/Components/MAC_F16_HPA.py
export NICE=19

echo "--- 1. 精确适配签名（只动第 90 行以后的 MAD_MIX 类）---"
sed -n "90,96p" $F
sed -i "90,\$ { s/def __call__(self, writer, m, innerUnroll):/def __call__(self, writer, tPA, tPB, m, innerUnroll):/; s/writer\.tPA/tPA/g; s/writer\.tPB/tPB/g }" $F
echo "  after:"
sed -n "90,100p" $F | grep -n "def __call__" || true
grep -c "tPA\[" $F

echo "--- 2. 语法自检 ---"
python3 -c "import ast,io; ast.parse(io.open(\"$F\",encoding=\"utf-8\").read()); print(\"  syntax OK\")"

echo "--- 3. 生成 f16 库（gfx906，yaml）---"
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
cd /out/work
rm -rf /out/gen10; mkdir -p /out/gen10
nice -n 19 timeout 900 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906h /out/gen10 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 3 2>&1 | tail -10
echo "--- 4. 产物 ---"
ls -l /out/gen10/library/gfx906 2>/dev/null | head -8
for f in /out/gen10/library/gfx906/*.hsaco; do
  [ -e "$f" ] || continue
  echo "  $f"
  strings "$f" | grep -m1 "amdhsa.target" || true
done
echo "=== gen10 end $(date +%F" "%T)"
'
} >> "$LOG" 2>&1
sed -n "/=== gen10 start/,\$p" "$LOG" | tail -30
