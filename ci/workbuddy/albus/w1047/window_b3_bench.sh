#!/bin/bash
# W1047: clean-GPU B3 HC bench window. No engine/config install.
set -u
C=strata166-407
W=/home/albus/strata166/tmp/w1047
IMG=strata-gfx906:0.2.11-101
LOG=$W/window_b3_bench2.log
mkdir -p "$W"
: > "$LOG"

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

restore() {
  log "RESTORE: starting production container $C"
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 20 || true)
    if echo "$st" | grep -q ok; then
      log "RESTORE: health ok after ${i}s"
      docker inspect -f 'RESTORE state={{.State.Status}} restarts={{.RestartCount}}' "$C" | tee -a "$LOG"
      return 0
    fi
    sleep 1
  done
  log "RESTORE FAIL: health did not return"
  return 1
}
trap restore EXIT INT TERM

log "DOWNTIME STARTS NOW"
docker stop -t 20 "$C" >/dev/null
for i in $(seq 1 20); do
  n=$(pgrep -x strata-host | wc -l)
  v=$(rocm-smi --showmeminfo vram 2>/dev/null | awk '/Total Used Memory/{print $NF; exit}')
  log "settle $i engines=$n vram_used=${v:-NA}"
  [ "$n" = 0 ] && [ "${v:-999999999999}" -lt 2000000000 ] && break
  sleep 2
done
n=$(pgrep -x strata-host | wc -l)
v=$(rocm-smi --showmeminfo vram 2>/dev/null | awk '/Total Used Memory/{print $NF; exit}')
if [ "$n" != 0 ] || [ "${v:-999999999999}" -ge 2000000000 ]; then
  log "PRECHECK FAIL engines=$n vram=$v"
  exit 1
fi

run_bench() {
  local mode=$1 val=$2
  log "=== clean fused_gr_bench $mode STRATA_HC_DOWN_DP4A=$val ==="
  docker run --rm --name qq_b3_$mode --device=/dev/kfd --device=/dev/dri \
    -e STRATA_HC_DOWN_DP4A=$val -e STRATA_TSUM=0 -e STRATA_BENCH_QMIXED=1 \
    -v /home/albus/strata166/build-masterp:/out "$IMG" \
    bash -lc 'timeout 420 /out/fused_gr_bench 64 1 8 3' 2>&1 | tee -a "$LOG"
  return ${PIPESTATUS[0]}
}

run_bench off 0 || { log "bench off failed"; exit 2; }
run_bench on  1 || { log "bench on failed";  exit 3; }
run_bench off2 0 || { log "bench off2 failed"; exit 4; }
run_bench on2  1 || { log "bench on2 failed";  exit 5; }

log "BENCH WINDOW DONE"
exit 0
