#!/bin/bash
# W844: A/B —— n4 (引擎 0.1.54 / 0.2.8 树) vs 0.1.55g (引擎 0.1.55 / v0.2.9 树)
# 纪律：① 温和重启 stop -t 30 → 等 exited → start；② 每臂比对 /metrics requests 增量，检出外来请求即标记
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
NA4=/data/bin/strata-0.1.54n4
NB=/data/bin/strata-0.1.55g
STAMP=$(date +%H%M%S)
ARMS="${ARMS:-A B A2}"
OUT=$DATA/w844_ab_$STAMP.txt
cp /home/albus/strata166/gfx029-build/strata-0.1.55g $DATA/bin/strata-0.1.55g && chmod +x $DATA/bin/strata-0.1.55g
cp "$CFG" /tmp/w844_prod.json
restore() {
  cp /tmp/w844_prod.json "$CFG" 2>/dev/null
  docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1
  for i in $(seq 1 480); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored $(date +%H:%M:%S)" >> "$OUT"
}
trap restore EXIT

setcfg() {
  python3 - "$CFG" "$1" <<'PYX'
import json, sys
cfg, exe = sys.argv[1], sys.argv[2]
base = json.load(open("/tmp/w844_prod.json"))
d = dict(base); d["exe"] = exe
assert set(d.keys()) == set(base.keys())
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  cfg exe=%s args_n=%d env_n=%d" % (exe, len(d["args"]), len(d.get("env") or {})))
PYX
}

reqcount() { curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin).get('totals',{}).get('requests',0))" 2>/dev/null || echo -1; }

run() {
  local arm=$1 exe=$2
  setcfg "$exe" >> "$OUT"
  docker stop -t 30 "$C" >/dev/null 2>&1
  for i in $(seq 1 60); do [ "$(docker inspect -f '{{.State.Status}}' $C)" = "exited" ] && break; sleep 1; done
  docker start "$C" >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 600); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  echo "=== ARM $arm exe=$(basename $exe) ready=${ok}s $(date +%H:%M:%S)" >> "$OUT"
  [ "$ok" = "0" ] && { echo "  ABORT arm $arm: 未就绪" >> "$OUT"; return 1; }
  local r0=$(reqcount)
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$arm" "$DATA/w844_read_$arm.json" 3718,6666,24000 2 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
  ( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 "$arm" "$DATA/w844_gen_$arm.json" dec_corpus.json 200 3 ) >> "$OUT" 2>&1
  local r1=$(reqcount)
  echo "  REQ arm=$arm before=$r0 after=$r1 delta=$((r1-r0)) （期望 11：warm2+read6+gen3；多出来的就是外来请求）" >> "$OUT"
  docker exec "$C" bash -lc "grep -aE 'read in [0-9]+ ms' $LOG | tail -9" | sed 's/^/  READ /' >> "$OUT"
  docker exec "$C" bash -lc "grep -a 'engine started\\|strata 0\\.1\\.5' $LOG | tail -2" | sed 's/^/  VER /' >> "$OUT"
  echo >> "$OUT"
}

echo "# W844 A/B 起始 $STAMP   A=n4(0.1.54/0.2.8树)  B=0.1.55g(0.1.55/0.2.9树)" >> "$OUT"
for a in $ARMS; do
  case "$a" in
    A)  run A  "$NA4" ;;
    B)  run B  "$NB" ;;
    A2) run A2 "$NA4" ;;
  esac
done
cp /tmp/w844_prod.json "$CFG"
docker stop -t 30 "$C" >/dev/null 2>&1; sleep 2; docker start "$C" >/dev/null 2>&1
for i in $(seq 1 480); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored-prod ${i}s $(date +%H:%M:%S)" >> "$OUT"; break; }; sleep 1; done
trap - EXIT
echo "== DONE $OUT"
