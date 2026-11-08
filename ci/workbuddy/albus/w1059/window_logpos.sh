#!/bin/bash
# W1059: LOGPOS window, 5 arms, one-shot container per arm, trap restore.
#   s001a/s001b : exe -001 (floor pair, must be byte-identical)
#   s010        : exe -010 (K10 stack)            -> P392 stack gate vs s001a
#   sum0/sum1   : exe -sumx, STRATA_SUMX=0/1      -> R101 single-variable gate
# Protocol = W824 §10: STRATA_LOGPOS + STRATA_LOGPOS_TOPK=64 + STRATA_PREFILL_CPU_SHARE=0.
set -u
T=/home/albus/strata166/tmp
D=/home/albus/strata166/data
W=$D/w1059
IMG=strata-gfx906:0.2.11-101
NAME=w1059kl
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

exec 9>/tmp/w1059_kl.lock
flock -n 9 || { echo "REFUSING: another window holds /tmp/w1059_kl.lock"; exit 4; }

: > "$LOG"
{
  echo "### W1059 LOGPOS window start $(date +%F' '%T)"
  for spec in "s001a strata-0.1.57-001 0" "s001b strata-0.1.57-001 0" "s010 strata-0.1.57-010 0" "sum0 strata-0.1.57-sumx 0" "sum1 strata-0.1.57-sumx 1"; do
    set -- $spec
    ARM=$1; EXE=$2; SX=$3
    echo "=== ARM $ARM  exe=$EXE  STRATA_SUMX=$SX"
    python3 - "$ARM" "$EXE" "$SX" <<'PY'
import json, sys
arm, exe, sx = sys.argv[1:4]
live = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
orig = "/home/albus/strata166/tmp/w1057/cfg_a4_pre.bak"
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
env["STRATA_LOGPOS"] = "/data/w1059/logpos_%s.tsv" % arm
env["STRATA_LOGPOS_TOPK"] = "64"
env["STRATA_PREFILL_CPU_SHARE"] = "0"
env["STRATA_SUMX"] = sx
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
out = "/home/albus/strata166/data/w1059/cfg_%s.json" % arm
json.dump(d, open(out, "w", encoding="utf-8"), indent=2)
print("cfg armed:", out, "exe=", d["exe"], "env_n=", len(env))
PY
    timeout 90 docker stop -t 20 "$PROD" >/dev/null 2>&1 && echo "  production stopped" || echo "  production stop timeout/absent"
    sleep 2
    docker rm -f "$NAME" >/dev/null 2>&1
    docker run -d --name "$NAME" \
      --ulimit memlock=-1 --ipc host --security-opt label=disable \
      --device=/dev/kfd --device=/dev/dri --group-add video \
      -p 8090:8090 -v /models:/models -v "$D":/data \
      -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
      "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w1059/cfg_$ARM.json --port 8090" >/dev/null
    READY=""
    for i in $(seq 1 900); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { READY=$i; break; }
      sleep 1
    done
    echo "  READY=${READY}s"
    if [ -z "$READY" ]; then echo "  !! arm $ARM never ready"; docker logs "$NAME" 2>&1 | tail -12 | cut -c1-160; continue; fi
    cd "$T" || exit 1
    python3 mt_kl.py kl_corpus.json 8090 "$ARM" "$W/out_$ARM.json" 2>&1 | tail -8
    ls -la "$W/logpos_$ARM.tsv" 2>/dev/null && wc -l < "$W/logpos_$ARM.tsv" | sed 's/^/  rows: /'
    echo "  md5 $(md5sum "$W/logpos_$ARM.tsv" 2>/dev/null | cut -d' ' -f1)"
  done
  echo "### W1059 LOGPOS window end $(date +%F' '%T)"
} >> "$LOG" 2>&1
echo WINDOW_RC=$?
grep -E "ARM |READY|rows:|md5|cfg armed|restore|HEALTHY" "$LOG" | tail -40
