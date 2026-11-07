#!/bin/bash
set -u
SRC=/home/albus/strata166/rocm-libs
OUTD=/home/albus/strata166/data/w859_hblt
W858=/home/albus/strata166/data/w858_hblt
V20=/home/albus/strata166/data/w860_vega20
LOG=/home/albus/strata166/data/w860_gen15.log
IMG=strata-gfx906:0.2.9-101
echo "gen15 start"
docker run --rm --cpus=4 -v "$SRC":/src -v "$OUTD":/out -v "$W858":/g858 -v "$V20":/v20 "$IMG" bash /v20/inner_hand.sh 2>&1 | tee "$LOG"
echo "gen15 end"
