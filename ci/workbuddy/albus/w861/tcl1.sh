#!/bin/bash
# W861-A: 用 TensileCreateLibrary 直接吃 rocBLAS 原生 vega20 HHS logic -> hipBLASLt msgpack 库
set -u
S=/home/albus/strata166/rocm-libs
V20=/home/albus/strata166/data/w860_vega20
W858=/home/albus/strata166/data/w858_hblt
OUTD=/home/albus/strata166/data/w861_hblt
LOG=/home/albus/strata166/data/w861_tcl1.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUTD"
: > "$LOG"
echo "tcl1 start $(date -u +%FT%TZ)"
docker run --rm --cpus=12 -v "$S":/src -v "$V20":/v20 -v "$W858":/g858 -v "$OUTD":/out "$IMG" bash -lc '
set -u
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:$PATH
cd /tmp
python3 -m Tensile.TensileCreateLibrary \
  --architecture=gfx906 \
  --cxx-compiler=/opt/rocm/llvm/bin/clang++ \
  --library-format=msgpack \
  --jobs 12 --no-enumerate --disable-asm-comments \
  /v20/logic /out/tcl1 HIP 2>&1 | tail -40
echo "rc=$?"
echo "--- artifacts ---"
find /out/tcl1 -type f 2>/dev/null | head -30
ls -la /out/tcl1 2>/dev/null | head -20
' 2>&1 | tee -a "$LOG"
echo "tcl1 end $(date -u +%FT%TZ)"
