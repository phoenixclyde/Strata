#!/bin/bash
set -u
SRC=/home/albus/strata166/rocm-libs
OUTD=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
V20=/home/albus/strata166/data/w860_vega20
LOG=/home/albus/strata166/data/w860_gen16.log
echo "gen16 start"
docker run --rm --cpus=4 --device /dev/kfd --device /dev/dri --group-add video \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
  -v "$SRC":/src -v "$OUTD":/out -v "$W858":/g858 -v "$V20":/v20 strata-gfx906:0.2.9-101 \
  bash /v20/inner_full.sh 2>&1 | tee "$LOG"
echo "gen16 end"
