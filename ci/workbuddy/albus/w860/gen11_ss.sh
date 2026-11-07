#!/bin/bash
# W860-B2：用"朴素 SS（f32、无 Bias/SAV/Activation）"的 gfx906 logic 生成库，再看 heuristic 能否命中。
# 全程 CPU-only（不给 --device），限 4 核 + nice 19。
set -u
SRC=/home/albus/strata166/rocm-libs
W859=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
TMP=/home/albus/strata166/tmp
LOG=/home/albus/strata166/data/w860_gen11.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== gen11 start $(date +%F" "%T)"
  docker run --rm --cpus=4 \
    -v "$SRC":/src:ro -v "$W859":/out -v "$W858":/g858 -v "$TMP":/in:ro "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
SB=$TL/Tensile/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml
mkdir -p /out/work /out/logic906ss
echo "--- 1. 派生朴素 SS logic ---"
python3 /in/mk_ss_logic.py "$SB" /out/logic906ss/logic_gfx906_SS.yaml

echo "--- 2. 生成库 ---"
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
cd /out/work
rm -rf /out/gen11; mkdir -p /out/gen11
nice -n 19 timeout 900 python3 $TL/Tensile/bin/TensileCreateLibrary /out/logic906ss /out/gen11 HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=yaml --no-enumerate -j 3 2>&1 | tail -8
echo "--- 3. 产物 ---"
ls -l /out/gen11/library/gfx906 2>/dev/null | head -6
echo "--- 4. 解名（应无 Bias/SAV）---"
grep -o "Cijk[A-Za-z0-9_]*" /out/gen11/library/gfx906/TensileLibrary_lazy_gfx906.yaml 2>/dev/null | sort -u | head -4
'
  echo "=== gen11 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== gen11 start/,\$p" "$LOG" | tail -26
