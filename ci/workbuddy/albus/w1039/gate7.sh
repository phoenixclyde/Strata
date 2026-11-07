#!/bin/bash
# W1039/P457: the discriminator arm.  ATTN_DPP=1 (bit 1) replaces warp_sum's implementation only -- it
# changes no arithmetic by construction, so it MUST be bit-identical to the baseline.
#   it also lands ~0.04  -> every OPT arm drifts, switch-independent
#   it lands 0           -> only the arms that read K by hand drift
# Control = g5_E.tsv (pa7, no switch), floor already proven against b12180 and pa8.
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/port-all
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
PROG=$W/gate7.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  local rc=$?
  docker rm -f qq7_DPP >/dev/null 2>&1
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
    log "RESTORE: container started (rc=$rc)"
  fi
  for i in $(seq 1 40); do
    curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
    sleep 3
  done
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "production is not b12180"
[ -f "$W/g5_E.tsv" ] || fail "control g5_E.tsv missing"
md5sum "$S/data/bin/strata-0.1.57-pa7" | tee -a "$PROG"

log "=== config for pa7 ==="
python3 - "$CFG" "$W" <<'PY' | tee -a "$PROG"
import io, json, sys
cfg, w = sys.argv[1], sys.argv[2]
d = json.load(io.open(cfg, encoding="utf-8-sig"))
d["exe"] = "/data/bin/strata-0.1.57-pa7"
a = d["args"]
for i, x in enumerate(a):
    if x == "--expert-profile-save" and i + 1 < len(a):
        a[i + 1] = w + "/qq-profile7.bin"
d["args"] = a
json.dump(d, io.open(w + "/qq_cfg7d.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("cfg exe=", d["exe"], "args=", len(a), "env=", len(d.get("env", {})))
PY

log "=== stop production ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 3
[ "$(pgrep -c -x strata-host)" = "0" ] || fail "engine still alive"

log "=== arm DPP (STRATA_GFX906_ATTN_DPP=1) ==="
docker run --rm --name qq7_DPP --device=/dev/kfd --device=/dev/dri \
  -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
  bash -lc "timeout 260 python3 /w/qq_k8v4.py run --config /w/qq_cfg7d.json --out /w/g7_DPP.tsv --ids /src/data/quant_quality/v1/set.ids.json --gpu-experts --env STRATA_GFX906_ATTN_DPP=1" \
  >> "$PROG" 2>&1
RC=$?
log "arm DPP rc=$RC  $( [ -f "$W/g7_DPP.tsv" ] && wc -l < "$W/g7_DPP.tsv" || echo 'no tsv')"
docker rm -f qq7_DPP >/dev/null 2>&1

log "=== compare: control (pa7, no switch) vs DPP ==="
docker run --rm -v "$SRC":/src -v "$W":/w "$IMG" bash -lc \
  "cd /src && python3 /w/qq_k8v4.py compare /w/g5_E.tsv /w/g7_DPP.tsv 2>&1 | tail -10" 2>&1 | tee -a "$PROG"

log "=== restore ==="
docker start $C >/dev/null || fail "docker start"
for i in $(seq 1 140); do
  curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
  sleep 3
done
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "restored exe wrong"
log "DONE"
trap - EXIT
