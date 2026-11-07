#!/bin/bash
set -u
C=strata166-407
W=/home/albus/strata166/tmp/w1047
IMG=strata-gfx906:0.2.11-101
LOG=$W/window_b3_n3.log
: > "$LOG"
log(){ echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
restore(){ docker start "$C" >/dev/null 2>&1 || true; for i in $(seq 1 90); do curl -s -m 3 localhost:8090/health 2>/dev/null | grep -q ok && { log "RESTORE ok ${i}s"; return 0; }; sleep 1; done; log RESTORE_FAIL; }
trap restore EXIT INT TERM
log "DOWNTIME STARTS NOW"
docker stop -t 20 "$C" >/dev/null
sleep 2
for rep in 1 2 3; do
  for mode in off on; do
    val=0; [ "$mode" = on ] && val=1
    docker run --rm --device=/dev/kfd --device=/dev/dri -e STRATA_HC_DOWN_DP4A=$val -e STRATA_TSUM=0 -e STRATA_BENCH_QMIXED=1 \
      -v /home/albus/strata166/build-masterp:/out "$IMG" \
      bash -lc "timeout 240 /out/fused_gr_bench 64 4 4 3" 2>&1 | tee -a "$LOG" | grep "COLD(3 sets) fast 2 T 4"
  done
done
log "N3 DONE"
