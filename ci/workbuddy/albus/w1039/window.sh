#!/bin/bash
# W1039: measure pa3 (port-all rebuilt on the b12180 llama tree) on the production path.
#   臂 ctl = 在产 b12180（不重启）
#   臂 b   = pa3 + STRATA_GFX906_ATTN_DP4A=1
#   臂 c   = pa3 + STRATA_GFX906_ATTN_DPP=1 + ATTN_LDS_PAD=1 + ROUTE_DPP=1
# 三次重启（b / c / 还原），每次约 45 s。config 备份 + md5 校验还原，健康失败即还原。
set -u
W=/home/albus/strata166/tmp/w1039
OLD=/home/albus/strata166/tmp/w1037
DATA=/home/albus/strata166/data
BIN=$DATA/bin
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
BASE_CT=/data/bin/strata-0.1.57-b12180
PA3_CT=/data/bin/strata-0.1.57-pa3
WANT_BASE=d24f8293b575fbcee6c097239d9599cb
WANT_PA3=b2ba6304ddc848100ba72140e49ef9a9
WANT_CFG=5e9b81e2f66ca48999766d2ae0201fb6
PROG=$W/window.log
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

# $1 = container exe path, $2 = "k=v;k=v" env pairs (empty = clear the OPT keys)
apply_cfg() {
  python3 - "$CFG" "$1" "$2" <<'PY' || return 1
import io, json, sys
p, exe, spec = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["exe"] = exe
env = d.get("env") or {}
# only the four OPT switches are ours; STRATA_GFX906_TUNED must survive (it is part of the baseline)
for k in ("STRATA_GFX906_ATTN_DP4A", "STRATA_GFX906_ATTN_DPP",
          "STRATA_GFX906_ATTN_LDS_PAD", "STRATA_GFX906_ROUTE_DPP",
          "STRATA_GFX906_Q8_GATHER8"):
    env.pop(k, None)
for item in [x for x in spec.split(";") if x]:
    k, v = item.split("=", 1)
    env[k] = v
d["env"] = env
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("exe=%s env_opt=%s" % (exe, {k: v for k, v in env.items() if k.startswith("STRATA_GFX906_")}))
PY
}

engine_pid() { docker exec $C sh -c 'ls /proc | grep -E "^[0-9]+$" | while read p; do grep -q strata-host /proc/$p/comm 2>/dev/null && echo $p; done' | head -1; }

show_env() {   # proves the switches reached the process, not just the config file
  local pid; pid=$(engine_pid)
  log "engine pid=$pid env=[$(docker exec $C sh -c "tr '\\0' '\\n' < /proc/$pid/environ 2>/dev/null | grep STRATA_GFX906 | tr '\\n' ' '")]"
}

start_with() {  # $1 exe(ct) $2 env spec $3 label
  docker stop -t 30 $C >/dev/null || fail "stop before $3"
  apply_cfg "$1" "$2" >> "$PROG" 2>&1 || fail "config rewrite $3"
  docker start $C >/dev/null || fail "start $3"
  wait_health 420 || fail "$3 did not become healthy"
  local run; run=$(pgrep -a -x strata-host | awk '{print $2}')
  [ "$run" = "$1" ] || fail "running exe is $run, not $1"
  show_env
}

restore() {
  local rc=$?
  if [ -f "$W/cfg_window.bak" ]; then
    cp -f "$W/cfg_window.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_window.bak" "$CFG"
    [ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || sudo -n cp -f "$W/cfg_window.bak" "$CFG"
    log "RESTORE (rc=$rc) cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
    [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" = "true" ] || docker start $C >/dev/null 2>&1
    wait_health 420 || log "WARN health did not return"
  fi
}

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container down"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "$BASE_CT" ] || fail "production is not b12180"
md5sum "$BIN/strata-0.1.57-b12180" | grep -q $WANT_BASE || fail "b12180 md5"
md5sum "$BIN/strata-0.1.57-pa3" | grep -q $WANT_PA3 || fail "pa3 md5"
[ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || fail "config md5 not the expected baseline"
cp -f "$CFG" "$W/cfg_window.bak"
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== arm ctl (b12180, no restart) 1/2 ==="
python3 "$W/ab_w1039.py" "$W/arm_ctl.json" ctl >> "$PROG" 2>&1 || fail "ctl 1"
date +%s%N > "$OLD/salt"
log "=== arm ctl 2/2 ==="
python3 "$W/ab_w1039.py" "$W/arm_ctl2.json" ctl2 >> "$PROG" 2>&1 || fail "ctl 2"

log "=== arm b: pa3 + ATTN_DP4A ==="
start_with "$PA3_CT" "STRATA_GFX906_ATTN_DP4A=1" "arm_b"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/arm_dp4a.json" dp4a >> "$PROG" 2>&1 || fail "dp4a 1"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/arm_dp4a2.json" dp4a2 >> "$PROG" 2>&1 || fail "dp4a 2"

log "=== arm c: pa3 + DPP + LDS_PAD + ROUTE_DPP ==="
start_with "$PA3_CT" "STRATA_GFX906_ATTN_DPP=1;STRATA_GFX906_ATTN_LDS_PAD=1;STRATA_GFX906_ROUTE_DPP=1" "arm_c"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/arm_dpp.json" dpp >> "$PROG" 2>&1 || fail "dpp 1"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/arm_dpp2.json" dpp2 >> "$PROG" 2>&1 || fail "dpp 2"

log "=== restore b12180 ==="
docker stop -t 30 $C >/dev/null || fail "stop before restore"
cp -f "$W/cfg_window.bak" "$CFG" || sudo -n cp -f "$W/cfg_window.bak" "$CFG"
[ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || fail "config md5 after restore"
docker start $C >/dev/null || fail "start after restore"
wait_health 420 || fail "restored engine unhealthy"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "$BASE_CT" ] || fail "restored exe wrong"
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
trap - EXIT
