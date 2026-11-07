#!/bin/bash
set -u
S=/home/albus/strata166
W=$S/tmp/w1046
IMG=strata-gfx906:0.2.11-101

echo "=== gr_parity (candidate build, DP4A off) ==="
docker run --rm --device=/dev/kfd --device=/dev/dri -e STRATA_HC_DOWN_DP4A=0 \
  -v $S/build-masterp:/out "$IMG" bash -lc 'timeout 420 /out/gr_parity' 2>&1 | tee $W/gr_parity_off.log | tail -25

for mode in off on; do
  val=0; [ "$mode" = on ] && val=1
  echo "=== contended exploratory cold Q8 bench: $mode ==="
  docker run --rm --device=/dev/kfd --device=/dev/dri -e STRATA_HC_DOWN_DP4A=$val -e STRATA_TSUM=0 \
    -v $S/build-masterp:/out "$IMG" bash -lc 'timeout 300 /out/fused_gr_bench 1 4 4 2' 2>&1 \
    | tee "$W/cold_$mode.log" | grep -E 'COLD|Q8 vs|differing' | tail -24
done
