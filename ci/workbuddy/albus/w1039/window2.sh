#!/bin/bash
# W1039 window 2: pa4 puts the OPT dispatch inside the query-swizzle branch (the one production runs).
#   ctl = b12180 (no restart) | b = pa4 + ATTN_DP4A | c = pa4 + ATTN_DPP
# Three restarts (b / c / restore), ~45 s each.
set -u
W=/home/albus/strata166/tmp/w1039
OLD=/home/albus/strata166/tmp/w1037
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
BASE_CT=/data/bin/strata-0.1.57-b12180
PA4_CT=/data/bin/strata-0.1.57-pa4
WANT_BASE=d24f8293b575fbcee6c097239d9599cb
WANT_PA4=49937458627b0a40038e237cae352a06
WANT_CFG=5e9b81e2f66ca48999766d2ae0201fb6
PROG=$W/window2.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

wait_health() {
  local t0=$1 t=$1
  while [ "$t" -gt 0 ]; do
    if curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"'; then
      log "health ok after $(( t0 - t ))s"; return 0
    fi
    sleep 3; t=$((t - 3))
  done
  return 1
}

apply_cfg() {
  python3 - "$CFG" "$1" "$2" <<'PY' || return 1
import io, json, sys
p, exe, spec = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["exe"] = exe
env = d.get("env") or {}
for k in ("STRATA_GFX906_ATTN_DP4A", "STRATA_GFX906_ATTN_DPP",
          "STRATA_GFX906_ATTN_LDS_PAD", "STRATA_GFX906_ROUTE_DPP",
          "STRATA_GFX906_Q8_GATHER8"):
    env.pop(k, None)
for item in [x for x in spec.split(";") if x]:
    k, v = item.split("=", 1)
    env[k] = v
d["env"] = env
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("exe=%s opts=%s" % (exe, {k: v for k, v in env.items() if k.startswith("STRATA_GFX906_ATTN") or k.endswith("ROUTE_DPP")}))
PY
}

engine_pid() { docker exec $C sh -c 'for p in /proc/[0-9]*; do grep -q strata-host $p/comm 2>/dev/null && basename $p && break; done'; }
show_env() {
  local pid; pid=$(engine_pid)
  log "pid=$pid env=[$(docker exec $C sh -c "tr '\\0' '\\n' < /proc/$pid/environ | grep -E 'ATTN_|ROUTE_DPP' | tr '\\n' ' '")]"
}

sanity() {   # a wrong OPT path would show up as garbage text, not as a slow kernel
  python3 - <<'PY' 2>&1 | tee -a "$PROG"
import json, urllib.request
body = json.dumps({"model": "x", "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                   "max_tokens": 8, "temperature": 0.0}).encode()
r = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                           headers={"Content-Type": "application/json"})
d = json.loads(urllib.request.urlopen(r, timeout=180).read())
print("SANITY:", repr(d["choices"][0]["message"]["content"])[:120])
PY
}

start_with() {  # $1 exe $2 env spec $3 label $4 want md5
  docker stop -t 30 $C >/dev/null || fail "stop before $3"
  apply_cfg "$1" "$2" >> "$PROG" 2>&1 || fail "config $3"
  docker start $C >/dev/null || fail "start $3"
  wait_health 420 || fail "$3 unhealthy"
  local run; run=$(pgrep -a -x strata-host | awk '{print $2}')
  [ "$run" = "$1" ] || fail "running $run != $1"
  show_env
  [ "$(md5sum "$DATA/bin/$(basename $1)" | cut -d' ' -f1)" = "$4" ] || fail "md5 of $1"
}

restore() {
  local rc=$?
  if [ -f "$W/cfg_window2.bak" ]; then
    cp -f "$W/cfg_window2.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_window2.bak" "$CFG"
    [ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || sudo -n cp -f "$W/cfg_window2.bak" "$CFG"
    log "RESTORE (rc=$rc) cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
    [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" = "true" ] || docker start $C >/dev/null 2>&1
    wait_health 420 || log "WARN health did not return"
  fi
}

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "$BASE_CT" ] || fail "production is not b12180"
md5sum "$DATA/bin/strata-0.1.57-b12180" | grep -q $WANT_BASE || fail "b12180 md5"
md5sum "$DATA/bin/strata-0.1.57-pa4" | grep -q $WANT_PA4 || fail "pa4 md5"
[ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || fail "config baseline"
cp -f "$CFG" "$W/cfg_window2.bak"
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== arm ctl 1/2 ==="
python3 "$W/ab_w1039.py" "$W/w2_ctl.json" ctl >> "$PROG" 2>&1 || fail "ctl1"
date +%s%N > "$OLD/salt"
log "=== arm ctl 2/2 ==="
python3 "$W/ab_w1039.py" "$W/w2_ctl2.json" ctl2 >> "$PROG" 2>&1 || fail "ctl2"

log "=== arm dp4a ==="
start_with "$PA4_CT" "STRATA_GFX906_ATTN_DP4A=1" dp4a "$WANT_PA4"
sanity
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/w2_dp4a.json" dp4a >> "$PROG" 2>&1 || fail "dp4a1"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/w2_dp4a2.json" dp4a2 >> "$PROG" 2>&1 || fail "dp4a2"

log "=== arm dpp ==="
start_with "$PA4_CT" "STRATA_GFX906_ATTN_DPP=1" dpp "$WANT_PA4"
sanity
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/w2_dpp.json" dpp >> "$PROG" 2>&1 || fail "dpp1"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/w2_dpp2.json" dpp2 >> "$PROG" 2>&1 || fail "dpp2"

log "=== restore b12180 ==="
docker stop -t 30 $C >/dev/null || fail "stop before restore"
cp -f "$W/cfg_window2.bak" "$CFG" || sudo -n cp -f "$W/cfg_window2.bak" "$CFG"
[ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || fail "config md5 after restore"
docker start $C >/dev/null || fail "start after restore"
wait_health 420 || fail "restored unhealthy"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "$BASE_CT" ] || fail "restored exe"
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
trap - EXIT
