#!/bin/bash
# W860-B5: reverse-engineer rocBLAS vega20 HHS_BH solutions into a Tensile config, then generate gfx906 f16 VALU kernels.
# CPU-only (no --device), 4 cores, nice 19.
set -u
SRC=/home/albus/strata166/rocm-libs
OUTD=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
V20=/home/albus/strata166/data/w860_vega20
LOG=/home/albus/strata166/data/w860_gen14.log
IMG=strata-gfx906:0.2.9-101
echo "gen14 start"
docker run --rm --cpus=4 \
  -v "$SRC":/src -v "$OUTD":/out -v "$W858":/g858 -v "$V20":/v20 "$IMG" \
  bash /v20/inner_gen14.sh 2>&1 | tee "$LOG"
echo "gen14 end"
tail -40 "$LOG"
