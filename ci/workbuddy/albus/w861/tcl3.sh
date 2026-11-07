#!/bin/bash
# W861-G2: block style + 展开锚点，再喂 TCL
set -u
S=/home/albus/strata166/rocm-libs
V20=/home/albus/strata166/data/w860_vega20
W858=/home/albus/strata166/data/w858_hblt
OUTD=/home/albus/strata166/data/w861_hblt
LOG=$OUTD/tcl3.log
mkdir -p "$OUTD/logic_blk2"
: > "$LOG"
{
echo "=== tcl3 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$S":/src -v "$V20":/v20 -v "$W858":/g858 -v "$OUTD":/out \
  -v /home/albus/w861_convert_logic2.py:/conv2.py:ro strata-gfx906:0.2.9-101 bash -lc '
set -u
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:$PATH
echo "--- 1) convert (block + no alias) ---"
python3 /conv2.py /v20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml /out/logic_blk2/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml
echo "--- 2) TCL (只看前 40 行 + 尾部) ---"
cd /tmp
python3 -m Tensile.TensileCreateLibrary \
  --architecture=gfx906 --cxx-compiler=/opt/rocm/llvm/bin/clang++ \
  --library-format=msgpack --jobs 12 --no-enumerate --disable-asm-comments \
  /out/logic_blk2 /out/tcl3 HIP > /out/tcl3.out 2>&1
echo "rc=$?"
echo "--- head ---"; head -20 /out/tcl3.out
echo "--- tail ---"; tail -20 /out/tcl3.out
echo "--- err scan ---"; grep -nE "AssertionError|Error|Traceback|Rejecting|reject" /out/tcl3.out | head -8
echo "--- artifacts ---"
ls -la /out/tcl3 2>/dev/null | head -15
' 2>&1
echo "=== tcl3 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== tcl3 start/,\$p" "$LOG" | tail -55
