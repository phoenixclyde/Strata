#!/bin/bash
# W804 任务级门：12 道可判分短提示（prompt 250-310 token => chunk < 1024 => 落在 CPU share 的作用域）
#   三臂：A=share 0 / B=auto / C=auto（B、C 是同一个配置跑两遍 —— 规则 X：share 开之后必须 n>=2）
#   判「答对数」，不判逐字相同；答案由语料生成器自己算出，无需人工核对
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w804_task_$STAMP.txt
MAXT=64
WANT_ENV=13          # 生产 12 + DBG_CPU_GATE
N_TASK=$(python3 -c "import json;print(len(json.load(open('task_corpus.json'))['tasks']))")
cp "$CFG" /tmp/w804_task_prod.json
restore_cfg() {
  cp /tmp/w804_task_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W804 task gate $STAMP max_tokens=$MAXT tasks=$N_TASK" > "$OUT"
echo "  arms: A=share 0 / B=auto / C=auto(同配置第二遍)" >> "$OUT"
python3 -c "import json,hashlib;b=open('task_corpus.json','rb').read();print('  corpus sha16=%s'%hashlib.sha256(b).hexdigest()[:16])" >> "$OUT"

setarm() {
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
share = "0" if arm == "A" else "auto"
d = json.load(open(cfg))
e = dict(d.get("env") or {})
e["STRATA_PREFILL_CPU_SHARE"] = share
e["STRATA_PREFILL_CPU_SHARE_MAX"] = "1024"
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
  local got sh
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  sh=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_PREFILL_CPU_SHARE="' 2>/dev/null)
  echo "  ENVCHECK want=$WANT_ENV got=${got:-?} ${sh:-?}" >> "$OUT"
  if [ "${got:-0}" != "$WANT_ENV" ]; then echo "!! ABORT env_n $got" >> "$OUT"; echo ABORT; exit 1; fi
  python3 mt_task.py 8090 "$arm" "$DATA/w804_task_$arm.json" task_corpus.json "$MAXT" >> "$OUT" 2>&1
  if [ ! -f "$DATA/w804_task_$arm.json" ]; then echo "!! ABORT no JSON $arm" >> "$OUT"; echo ABORT; exit 1; fi
  echo "  cpu_gate_share_lines=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -ac 'cpu gate:.*-> share')" >> "$OUT"
  slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
}

run A
run B
run C

cp /tmp/w804_task_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d share=%s'%(len(d['env']),d['env'].get('STRATA_PREFILL_CPU_SHARE')))" >> "$OUT"
echo "== DONE $OUT"
