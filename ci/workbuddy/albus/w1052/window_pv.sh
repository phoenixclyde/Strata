#!/bin/bash
# W1052: one-shot real PV dump via the probe binary.  cfg exe=pvprobe +
# STRATA_PV_DUMP, one 48-token chat request, restore cfg + cold restart.
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1052
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_pv.log
mkdir -p "$W"
: > "$LOG"
cp -f "$CFG" "$W/cfg_pv_pre.bak" || exit 1

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  cp -f "$W/cfg_pv_pre.bak" "$CFG" || true
  docker stop -t 25 "$C" >/dev/null 2>&1 || true
  sleep 2
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "RESTORE: health ok after ${i}s"; return 0; fi
    sleep 1
  done
  log "RESTORE FAIL"; return 1
}
trap restore EXIT INT TERM

python3 - "$CFG" "$W/cfg_pv_pre.bak" <<'PY'
import json, sys
live, orig = sys.argv[1], sys.argv[2]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
env["STRATA_PV_DUMP"] = "/data/pv_w1052.dump"
d["exe"] = "/data/bin/strata-0.1.57-pvprobe"
d["env"] = env
json.dump(d, open(live, "w", encoding="utf-8"), indent=2)
print("cfg armed: exe=pvprobe PV_DUMP=/data/pv_w1052.dump env_n=%d" % len(env))
PY

docker stop -t 25 "$C" >/dev/null 2>&1 || true
sleep 2
docker start "$C" >/dev/null 2>&1 || fail "docker start"
for i in $(seq 1 90); do
  st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
  if echo "$st" | grep -q ok; then log "health ok after ${i}s"; break; fi
  sleep 1
done

rm -f "$S/data/pv_w1052.dump"
log "=== one decode request ==="
python3 - <<'PY' | tee -a "$LOG"
import json, urllib.request
txt = "Give a short factual answer: what is the capital of France? Explain in two sentences. Unique pv probe marker 1."
body = json.dumps({"model": "strata", "messages": [{"role": "user", "content": txt}],
                   "max_tokens": 128, "temperature": 0}).encode()
req = urllib.request.Request("http://localhost:8090/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=600) as r:
    d = json.loads(r.read())
print("usage", d.get("usage"))
PY

log "=== pull dump (host path via /data mount) ==="
ls -la "$S/data/pv_w1052.dump" >>"$LOG" 2>&1 || log "dump file not found on /data"
log "=== done ==="
