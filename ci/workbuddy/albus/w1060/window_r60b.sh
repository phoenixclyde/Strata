#!/bin/bash
# W1060b: catch-up window -- timing arms (fixed run_timing path) + R46 QSA_DUMP + R79 F2 retry client.
set -u
T=/home/albus/strata166/tmp
D=/home/albus/strata166/data
W=$D/w1060
IMG=strata-gfx906:0.2.11-101
NAME=w1060win
PROD=strata166-407
LOG=$W/window_run2.log

restore() {
  echo "=== restore $(date +%F' '%T)"
  docker rm -f "$NAME" >/dev/null 2>&1
  docker start "$PROD" >/dev/null 2>&1
  for i in $(seq 1 420); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  production HEALTHY after ${i}s"; return; }
    sleep 1
  done
  echo "  !! production NOT healthy after 420s"
}
trap restore EXIT INT TERM
exec 9>/tmp/w1060_win.lock
flock -n 9 || { echo "REFUSING: lock held"; exit 4; }

: > "$LOG"
{
  echo "### W1060b window start $(date +%F' '%T)"
  arm() {
    local ARM=$1 EXE=$2 EXTRA_ENV=$3
    echo "=== ARM $ARM  exe=$EXE"
    python3 - "$ARM" "$EXE" "$EXTRA_ENV" <<'PY'
import json, sys
arm, exe, extra = sys.argv[1:4]
orig = "/home/albus/strata166/tmp/w1057/cfg_a4_pre.bak"
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
env["STRATA_PREFILL_CPU_SHARE"] = "0"
for kv in extra.split(","):
    if "=" in kv:
        k, v = kv.split("=", 1)
        env[k] = v
d["exe"] = "/data/bin/" + exe
d["env"] = env
args = []
skip = False
for a in d.get("args", []):
    if skip:
        skip = False
        continue
    if a == "--conversation-cache-mib":
        args += [a, "0"]
        skip = True
        continue
    args += [a]
d["args"] = args
out = "/home/albus/strata166/data/w1060/cfg_%s.json" % arm
json.dump(d, open(out, "w", encoding="utf-8"), indent=2)
print("cfg armed:", out, "exe=", d["exe"])
PY
    timeout 90 docker stop -t 20 "$PROD" >/dev/null 2>&1 && echo "  production stopped" || echo "  stop timeout/absent"
    sleep 2
    docker rm -f "$NAME" >/dev/null 2>&1
    docker run -d --name "$NAME" \
      --ulimit memlock=-1 --ipc host --security-opt label=disable \
      --device=/dev/kfd --device=/dev/dri --group-add video \
      -p 8090:8090 -v /models:/models -v "$D":/data \
      -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
      "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w1060/cfg_$ARM.json --port 8090" >/dev/null
    local READY=""
    for i in $(seq 1 900); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { READY=$i; break; }
      sleep 1
    done
    echo "  READY=${READY}s"
  }

  arm A0 strata-0.1.57-hc4b "STRATA_QSA_DUMP=/data/w1060/qsa_dump_a0.bin"
  cd "$T/w1060" && python3 run_timing.py 8090 A0 32768,65536 3 "$W/timing_A0.json" 2>&1 | tail -9
  cd "$T/w1060" && python3 run_timing.py 8090 A0b 2048,6144,12288 3 "$W/timing_A0b.json" 2>&1 | tail -9
  docker logs "$NAME" 2>&1 | grep -a "prefill timing" | tail -20 | sed 's/^/  T /'

  arm B0 strata-0.1.57-strk ""
  cd "$T/w1060" && python3 run_timing.py 8090 B0 32768,65536 3 "$W/timing_B0.json" 2>&1 | tail -9
  docker logs "$NAME" 2>&1 | grep -a "prefill timing" | tail -14 | sed 's/^/  T /'

  rm -f "$W/fatal_once.flag"
  arm F2 strata-0.1.57-hc4b "STRATA_INJECT_FATAL=2,STRATA_INJECT_FATAL_ONCE=/data/w1060/fatal_once.flag"
  cd "$T/w1060" && timeout 300 python3 f2_client.py 8090 F2 "$W/out_F2.json" 2>&1 | tail -10

  echo "### W1060b window end $(date +%F' '%T)"
} >> "$LOG" 2>&1
echo WINDOW_RC=$?
grep -E "ARM |READY|T size|prefill timing|F2|t[123] |HEALTHY|restore" "$LOG" | tail -40
