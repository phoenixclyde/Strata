#!/bin/bash
# W861-G3: 9 元素补齐到 12 元素（含 data[11]=distance），再喂 TCL
set -u
S=/home/albus/strata166/rocm-libs
V20=/home/albus/strata166/data/w860_vega20
W858=/home/albus/strata166/data/w858_hblt
OUTD=/home/albus/strata166/data/w861_hblt
LOG=$OUTD/tcl7.log
mkdir -p "$OUTD/logic_blk6"
: > "$LOG"
{
echo "=== tcl7 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$S":/src -v "$V20":/v20 -v "$W858":/g858 -v "$OUTD":/out \
  -v /home/albus/w861_convert_logic6.py:/conv6.py:ro strata-gfx906:0.2.9-101 bash -lc '
set -u
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:$PATH
echo "--- 1) 9 -> 12 ---"
python3 /conv6.py /v20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml /out/logic_blk6/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml Euclidean
echo "--- 2) TCL ---"
cd /tmp
python3 -m Tensile.TensileCreateLibrary \
  --architecture=gfx906 --cxx-compiler=/opt/rocm/llvm/bin/clang++ \
  --library-format=msgpack --jobs 12 --no-enumerate --disable-asm-comments \
  /out/logic_blk6 /out/tcl7 HIP > /out/tcl7.out 2>&1
echo "rc=$?"
echo "--- tail 25 ---"; tail -25 /out/tcl7.out
echo "--- err scan ---"; grep -nE "FATAL|AssertionError|Traceback|Error|Rejecting solution" /out/tcl7.out | head -10
echo "--- artifacts ---"
ls -la /out/tcl7 2>/dev/null | head -20
' 2>&1
echo "=== tcl7 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== tcl7 start/,\$p" "$LOG" | tail -50
