#!/bin/bash
# W1037 / R103 window.  Three arms on one candidate binary, one restart per arm change, verified restore.
#
#   arm ctl  = strata-0.1.57-001            (production, no port switches; measured first, no restart)
#   arm b    = strata-0.1.57-pa1 + ATTN_DP4A=1                        (B1+B2: attention scores on dp4a)
#   arm c    = pa1 + ATTN_DP4A=1 + ATTN_DPP=1 + ATTN_LDS_PAD=1 + ROUTE_DPP=1   (+ the bitwise trio A1/A2/A3)
#
# Inherited defects from the W1036 v1 script, all fixed here:
#   * `exe` must be the path the CONTAINER sees (/data/bin/...), never a host path;
#   * restore is verified by md5 and retried once with sudo, then aborts;
#   * the TERM handler exits (v1 resumed after the signal);
#   * every arm is warmed up and every timing line is retried (the engine drops the first 2 requests).
set -u
W=/home/albus/strata166/tmp/w1037
DATA=/home/albus/strata166/data
BIN=$DATA/bin
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
CAND_SRC=/home/albus/strata166/build-port2/strata
CAND_HOST=$BIN/strata-0.1.57-pa1
CAND_CT=/data/bin/strata-0.1.57-pa1
ORIG_CT=/data/bin/strata-0.1.57-001
WANT_MD5=53ac61e0c663a6a46b7a5aa2e610bf43
PROG=$W/progress.log
: > "$PROG"

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

wait_health() {
  local t0 t=$1
  t0=$t
  while [ "$t" -gt 0 ]; do
    if curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"'; then
      log "health ok after $(( t0 - t ))s"; return 0
    fi
    sleep 3; t=$((t - 3))
  done
  return 1
}

# $1 = container path of the engine, $2.. = K=V switch pairs to inject (empty = keep production env)
set_cfg() {
  local exe=$1; shift
  python3 - "$CFG" "$exe" "$@" <<'PY' || return 1
import io, json, sys
p, exe, kv = sys.argv[1], sys.argv[2], sys.argv[3:]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["exe"] = exe
env = d.get("env") or {}
for k in ("STRATA_GFX906_ATTN_DP4A", "STRATA_GFX906_ATTN_DPP",
          "STRATA_GFX906_ATTN_LDS_PAD", "STRATA_GFX906_ROUTE_DPP", "STRATA_GFX906_Q8_GATHER8"):
    env.pop(k, None)
for item in kv:
    k, _, v = item.partition("=")
    env[k] = v
d["env"] = env
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("cfg exe=", exe, "switches=", kv)
PY
}

restore() {
  local rc=$?
  log "RESTORE (rc=$rc)"
  [ -f "$W/cfg.bak" ] || { log "FATAL: no config backup"; return 1; }
  cp -f "$W/cfg.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg.bak" "$CFG"
  local now; now=$(md5sum "$CFG" | cut -d' ' -f1)
  if [ "$now" != "$WANT_MD5" ]; then
    log "RESTORE: md5 $now != wanted, retrying with sudo"
    sudo -n cp -f "$W/cfg.bak" "$CFG"
    now=$(md5sum "$CFG" | cut -d' ' -f1)
  fi
  [ "$now" = "$WANT_MD5" ] || log "FATAL: config md5 still $now"
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  fi
  wait_health 420 || log "WARN: health did not come back after restore"
  log "restore done: cfg=$(md5sum "$CFG" | cut -d' ' -f1) state=$(docker inspect -f '{{.State.Status}}' $C)"
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

# ---- 0 preconditions ---------------------------------------------------------
log "=== preconditions ==="
[ -f "$CAND_SRC" ] || fail "candidate missing"
[ -f "$W/ab_w1037.py" ] || fail "harness missing"
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected exactly 1 engine process"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$CFG" | grep -q $WANT_MD5 || fail "config md5 changed before we started"
grep -q "$ORIG_CT" "$CFG" || fail "production exe is not $ORIG_CT"
cp -f "$CFG" "$W/cfg.bak"
md5sum "$W/cfg.bak" | grep -q $WANT_MD5 || fail "backup md5 mismatch"
log "cand md5=$(md5sum "$CAND_SRC" | cut -d' ' -f1) size=$(stat -c%s "$CAND_SRC")"
date +%s%N > "$W/salt"
log "salt=$(cat "$W/salt")"

# ---- 1 arm ctl (no restart) --------------------------------------------------
log "=== arm ctl ($ORIG_CT) ==="
python3 "$W/ab_w1037.py" "$W/arm_ctl.json" ctl >> "$PROG" 2>&1 || fail "ctl measurement failed"

# ---- 2 install candidate with the DP4A switch -------------------------------
log "=== arm b: install candidate + ATTN_DP4A ==="
cp -f "$CAND_SRC" "$CAND_HOST.new" || fail "cp candidate"
chmod 755 "$CAND_HOST.new"
mv -f "$CAND_HOST.new" "$CAND_HOST" || fail "mv candidate"
docker stop -t 30 $C >/dev/null || fail "docker stop"
set_cfg "$CAND_CT" STRATA_GFX906_ATTN_DP4A=1 >> "$PROG" 2>&1 || fail "config rewrite (b)"
grep -q "$CAND_CT" "$CFG" || fail "config still points at production"
docker start $C >/dev/null || fail "docker start (b)"
wait_health 420 || fail "candidate did not become healthy"
python3 "$W/ab_w1037.py" "$W/arm_b.json" b >> "$PROG" 2>&1 || fail "arm b measurement failed"

# ---- 3 arm c: add the bitwise trio ------------------------------------------
log "=== arm c: + ATTN_DPP + ATTN_LDS_PAD + ROUTE_DPP ==="
docker stop -t 30 $C >/dev/null || fail "docker stop (c)"
set_cfg "$CAND_CT" STRATA_GFX906_ATTN_DP4A=1 STRATA_GFX906_ATTN_DPP=1 \
        STRATA_GFX906_ATTN_LDS_PAD=1 STRATA_GFX906_ROUTE_DPP=1 >> "$PROG" 2>&1 || fail "config rewrite (c)"
docker start $C >/dev/null || fail "docker start (c)"
wait_health 420 || fail "arm c did not become healthy"
python3 "$W/ab_w1037.py" "$W/arm_c.json" c >> "$PROG" 2>&1 || fail "arm c measurement failed"

# ---- 4 restore ---------------------------------------------------------------
log "=== restore production ==="
docker stop -t 30 $C >/dev/null
cp -f "$W/cfg.bak" "$CFG" || sudo -n cp -f "$W/cfg.bak" "$CFG"
grep -q "$ORIG_CT" "$CFG" || fail "restore: config still points at the candidate"
docker start $C >/dev/null
wait_health 420 || fail "production did not come back"
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1) engines=$(pgrep -c -x strata-host)"
