#!/bin/bash
# W861-G: 旧 logic -> block style，喂 TCL 再试一次（纯 CPU，不碰生产）
set -u
S=/home/albus/strata166/rocm-libs
V20=/home/albus/strata166/data/w860_vega20
W858=/home/albus/strata166/data/w858_hblt
OUTD=/home/albus/strata166/data/w861_hblt
LOG=$OUTD/tcl2.log
mkdir -p "$OUTD/logic_blk"
: > "$LOG"
{
echo "=== tcl2 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$S":/src -v "$V20":/v20 -v "$W858":/g858 -v "$OUTD":/out \
  -v /home/albus/w861_convert_logic.py:/conv.py:ro strata-gfx906:0.2.9-101 bash -lc '
set -u
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:$PATH
echo "--- 1) flow -> block ---"
python3 /conv.py /v20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml /out/logic_blk/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml
echo "--- 2) 头 12 行（确认 block style）---"
head -12 /out/logic_blk/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml
echo "--- 3) TCL ---"
cd /tmp
python3 -m Tensile.TensileCreateLibrary \
  --architecture=gfx906 --cxx-compiler=/opt/rocm/llvm/bin/clang++ \
  --library-format=msgpack --jobs 12 --no-enumerate --disable-asm-comments \
  /out/logic_blk /out/tcl2 HIP 2>&1 | tail -35
echo "--- 4) artifacts ---"
ls -la /out/tcl2 2>/dev/null | head -20
find /out/tcl2 -name "*Mapping*" -o -name "*.hsaco" 2>/dev/null | head -6
' 2>&1
echo "=== tcl2 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== tcl2 start/,\$p" "$LOG" | tail -60
