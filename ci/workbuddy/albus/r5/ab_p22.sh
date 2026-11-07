#!/bin/bash
# W804：read 长扫描 × 三条 share 作用域（A=prod auto+MAX1024 / B=auto+MAX3072 / C=share 0）
#   目的：①P129（1-3K 段到底该不该交给 CPU）②在新的生产配置下重做相位账（W800 那张图已过期）
#   每臂：6 个尺寸 × 3 次，`STRATA_PREFILL_TIMING=1` + `STRATA_TRACE=1`
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w804_read_$STAMP.txt
SIZES=150,300,600,900,1500,2500
REPS=3
WANT_ENV=15          # 生产 12 项 + TIMING + TRACE + DBG_CPU_GATE
cp "$CFG" /tmp/w804_prod.json

echo "# W804 read sweep $STAMP sizes=$SIZES reps=$REPS" > "$OUT"
echo "  arms: A=auto/MAX1024(生产) B=auto/MAX3072 C=0" >> "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('start env_n=%d share=%s max=%s'%(len(d['env']),d['env'].get('STRATA_PREFILL_CPU_SHARE'),d['env'].get('STRATA_PREFILL_CPU_SHARE_MAX')))" >> "$OUT"

setarm() {   # $1=arm
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
share, mx = {"A": ("auto", "1024"), "B": ("auto", "3072"), "C": ("0", "1024")}[arm]
d = json.load(open(cfg))
e = dict(d.get("env") or {})
e["STRATA_PREFILL_CPU_SHARE"] = share
e["STRATA_PREFILL_CPU_SHARE_MAX"] = mx
e["STRATA_PREFILL_TIMING"] = "1"
e["STRATA_TRACE"] = "1"
e["STRATA_DBG_CPU_GATE"] = "1"
d["env"] = e
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
}

run() {
  local arm=$1
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s" >> "$OUT"
  local got
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  local sh
  sh=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_PREFILL_CPU_SHARE" | sort | tr "\n" " "' 2>/dev/null)
  echo "  ENVCHECK want=$WANT_ENV got=${got:-?} :: ${sh:-?}" >> "$OUT"
  if [ "${got:-0}" != "$WANT_ENV" ]; then echo "!! ABORT env_n $got != $WANT_ENV" >> "$OUT"; echo "ABORT"; exit 1; fi
  python3 mt_read.py 8090 "$arm" "$DATA/w804_read_$arm.json" "$SIZES" "$REPS" kl_pool.json >> "$OUT" 2>&1
  # 守卫：客户端必须真的产出结果，否则立刻中止（W804 第一车就是漏推语料，静默跑了两个空臂）
  if [ ! -f "$DATA/w804_read_$arm.json" ]; then
    echo "!! ABORT: client produced no JSON for arm $arm" >> "$OUT"; echo "ABORT client"; exit 1
  fi
  local n
  n=$(python3 -c "import json;print(len(json.load(open('$DATA/w804_read_$arm.json'))['results']))" 2>/dev/null)
  echo "  client_results=${n:-0} (want $(( $(echo "$SIZES" | tr ',' '\n' | wc -l) * REPS )))" >> "$OUT"
  if [ "${n:-0}" -lt $(( $(echo "$SIZES" | tr ',' '\n' | wc -l) * REPS )) ]; then
    echo "!! ABORT: only ${n:-0} results" >> "$OUT"; echo "ABORT results"; exit 1
  fi
  slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
  # 相位行不能截断（lib_a9 的 slice 会 cut -c1-160），这里单独取全文
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
  echo "  cpu_gate_share_lines=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -ac 'cpu gate:.*-> share')" >> "$OUT"
}

run A
run B
run C

cp /tmp/w804_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d share=%s max=%s'%(len(d['env']),d['env'].get('STRATA_PREFILL_CPU_SHARE'),d['env'].get('STRATA_PREFILL_CPU_SHARE_MAX')))" >> "$OUT"
echo "== DONE $OUT"
