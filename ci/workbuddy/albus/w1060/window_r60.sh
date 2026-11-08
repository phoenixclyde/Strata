#!/bin/bash
# W1060: window for R60 (stream-k A/B) + R89 (depth 1x/3x/6x) + R46 (QSA_DUMP) + R79 (inject fatal).
# 6 one-shot arms, trap restore (W1059 pattern). Production config untouched (per-arm cfg copies).
#   W     : hc4b LOGPOS warmup (P592 profile lesson)
#   A0    : hc4b TIMING 32K/64K x3 + 2K/6K/12K x3 (R89) + QSA_DUMP (R46)
#   B0    : strk TIMING 32K/64K x3
#   A1    : hc4b LOGPOS (R59 KL baseline)
#   B1    : strk LOGPOS (R59 KL candidate)
#   F     : hc4b + STRATA_INJECT_FATAL=2 + ONCE file (R79 behavior)
set -u
T=/home/albus/strata166/tmp
D=/home/albus/strata166/data
W=$D/w1060
IMG=strata-gfx906:0.2.11-101
NAME=w1060win
PROD=strata166-407
mkdir -p "$W"
LOG=$W/window_run.log

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

echo "== R79 static: production restart policy =="
docker inspect "$PROD" --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null || echo unknown

: > "$LOG"
{
  echo "### W1060 window start $(date +%F' '%T)"
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
print("cfg armed:", out, "exe=", d["exe"], "env_n=", len(env))
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

  arm W strata-0.1.57-hc4b ""
  cd "$T" && python3 mt_kl.py kl_corpus.json 8090 W "$W/out_W.json" 2>&1 | tail -3
  ls -la "$W/logpos_W.tsv" 2>/dev/null || ls -la "$D/w1059/logpos_W.tsv" 2>/dev/null || echo "  (logpos W written per cfg)"

  arm A0 strata-0.1.57-hc4b "STRATA_QSA_DUMP=/data/w1060/qsa_dump_a0.bin"
  cd "$T" && python3 run_timing.py 8090 A0 32768,65536 3 "$W/timing_A0.json" 2>&1 | tail -9
  cd "$T" && python3 run_timing.py 8090 A0b 2048,6144,12288 3 "$W/timing_A0b.json" 2>&1 | tail -9
  docker logs "$NAME" 2>&1 | grep -a "prefill timing" | tail -18 | sed 's/^/  T /'

  arm B0 strata-0.1.57-strk ""
  cd "$T" && python3 run_timing.py 8090 B0 32768,65536 3 "$W/timing_B0.json" 2>&1 | tail -9
  docker logs "$NAME" 2>&1 | grep -a "prefill timing" | tail -12 | sed 's/^/  T /'

  arm A1 strata-0.1.57-hc4b "STRATA_LOGPOS=/data/w1060/logpos_A1.tsv,STRATA_LOGPOS_TOPK=64"
  cd "$T" && python3 mt_kl.py kl_corpus.json 8090 A1 "$W/out_A1.json" 2>&1 | tail -3
  ls -la "$W/logpos_A1.tsv" 2>/dev/null && md5sum "$W/logpos_A1.tsv"

  arm B1 strata-0.1.57-strk "STRATA_LOGPOS=/data/w1060/logpos_B1.tsv,STRATA_LOGPOS_TOPK=64"
  cd "$T" && python3 mt_kl.py kl_corpus.json 8090 B1 "$W/out_B1.json" 2>&1 | tail -3
  ls -la "$W/logpos_B1.tsv" 2>/dev/null && md5sum "$W/logpos_B1.tsv"

  rm -f "$W/fatal_once.flag"
  arm F strata-0.1.57-hc4b "STRATA_INJECT_FATAL=2,STRATA_INJECT_FATAL_ONCE=/data/w1060/fatal_once.flag"
  cd "$T" && timeout 300 python3 mt_kl.py kl_corpus.json 8090 F "$W/out_F.json" 2>&1 | tail -5
  echo "  F: container state after inject: $(docker inspect -f '{{.State.Status}} exit={{.State.ExitCode}} restarts={{.RestartCount}}' "$NAME" 2>/dev/null)"
  docker logs "$NAME" 2>&1 | grep -a -iE "injected|fatal|restart" | tail -6 | sed 's/^/  F /'

  echo "### W1060 window end $(date +%F' '%T)"
} >> "$LOG" 2>&1
echo WINDOW_RC=$?
grep -E "ARM |READY|cfg armed|T size|prefill timing|F:|HEALTHY|restore|policy" "$LOG" | tail -50
