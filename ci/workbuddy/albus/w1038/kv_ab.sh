#!/bin/bash
# W1038: A/B  --kv k8v4 (在产)  vs  --kv int8   —— 只换一个 CLI 参数，其余全同。
# 两次重启（切 int8 + 还原），每臂两轮冒烟（2.5K×3 + 8K×2 + decode×3）。
# 安全：config 备份 + md5 校验还原；candidate/rollback 不涉及二进制；单引擎断言；健康失败即还原。
set -u
W=/home/albus/strata166/tmp/w1038
OLD=/home/albus/strata166/tmp/w1037
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
EXE_CT=/data/bin/strata-0.1.57-b12180
WANT_EXE=d24f8293b575fbcee6c097239d9599cb
PROG=$W/kvab.log
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

set_kv() {
  python3 - "$CFG" "$1" <<'PY' || return 1
import io, json, sys
p, val = sys.argv[1], sys.argv[2]
d = json.load(io.open(p, encoding="utf-8-sig"))
a = d["args"]
if "--kv" in a:
    i = a.index("--kv")
    old = a[i + 1]
    a[i + 1] = val
elif any(x.startswith("--kv=") for x in a):
    old = [x for x in a if x.startswith("--kv=")][0]
    a[a.index(old)] = "--kv=" + val
else:
    print("no --kv in args"); sys.exit(1)
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("kv %s -> %s" % (old, val))
PY
}

snap() {   # $1 = tag
  local slots vram
  slots=$(grep -E "expert cache [0-9]+ slots" "$DATA/strata-huihui-ud-iq4_xs.log" | tail -1)
  vram=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -i "used" | head -1 | tr -s ' ')
  log "SNAP[$1] $slots | $vram"
}

restore() {
  local rc=$?
  if [ -f "$W/cfg_kv.bak" ]; then
    cp -f "$W/cfg_kv.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_kv.bak" "$CFG"
    local now; now=$(md5sum "$CFG" | cut -d' ' -f1)
    [ "$now" = "$WANT_CFG" ] || { sudo -n cp -f "$W/cfg_kv.bak" "$CFG"; now=$(md5sum "$CFG" | cut -d' ' -f1); }
    log "RESTORE (rc=$rc) cfg=$(echo $now | cut -c1-12) want=$(echo $WANT_CFG | cut -c1-12)"
    [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" = "true" ] || docker start $C >/dev/null 2>&1
    wait_health 420 || log "WARN: health did not return after restore"
  fi
}

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected exactly 1 engine process"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
RUN=$(pgrep -a -x strata-host | awk '{print $2}')
[ "$RUN" = "$EXE_CT" ] || fail "running exe is $RUN"
md5sum "$DATA/bin/strata-0.1.57-b12180" | grep -q $WANT_EXE || fail "engine md5 mismatch"
grep -q '"k8v4"' "$CFG" || fail "production kv is not k8v4"
WANT_CFG=$(md5sum "$CFG" | cut -d' ' -f1)
log "cfg=$WANT_CFG exe=$RUN"
cp -f "$CFG" "$W/cfg_kv.bak"
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

snap before_k8v4
log "=== arm ctl (k8v4, no restart) 1/2 ==="
python3 "$OLD/ab_w1037.py" "$W/arm_kv_k8v4.json" k8v4 >> "$PROG" 2>&1 || fail "ctl 1"
date +%s%N > "$OLD/salt"
log "=== arm ctl (k8v4) 2/2 ==="
python3 "$OLD/ab_w1037.py" "$W/arm_kv_k8v4b.json" k8v4b >> "$PROG" 2>&1 || fail "ctl 2"

log "=== swap kv -> int8 ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
set_kv int8 >> "$PROG" 2>&1 || { set_kv k8v4 >/dev/null 2>&1; fail "config rewrite"; }
grep -q '"int8"' "$CFG" || fail "config does not say int8"
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "int8 engine did not become healthy"
RUN=$(pgrep -a -x strata-host | awk '{print $2}')
[ "$RUN" = "$EXE_CT" ] || fail "running exe is $RUN"
snap after_int8
date +%s%N > "$OLD/salt"
log "=== arm int8 1/2 ==="
python3 "$OLD/ab_w1037.py" "$W/arm_kv_int8.json" int8 >> "$PROG" 2>&1 || fail "int8 1"
date +%s%N > "$OLD/salt"
log "=== arm int8 2/2 ==="
python3 "$OLD/ab_w1037.py" "$W/arm_kv_int8b.json" int8b >> "$PROG" 2>&1 || fail "int8 2"

log "=== restore k8v4 ==="
cp -f "$W/cfg_kv.bak" "$CFG" || sudo -n cp -f "$W/cfg_kv.bak" "$CFG"
docker stop -t 30 $C >/dev/null || fail "stop before restore"
[ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || fail "config md5 after restore"
docker start $C >/dev/null || fail "start after restore"
wait_health 420 || fail "restored engine did not become healthy"
RUN=$(pgrep -a -x strata-host | awk '{print $2}')
[ "$RUN" = "$EXE_CT" ] || fail "restored exe is $RUN"
snap restored_k8v4
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
trap - EXIT
