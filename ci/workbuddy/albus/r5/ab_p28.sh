#!/bin/bash
# W805d 任务级门：chunk 8192 (A) vs 16384 (B) —— 判 chunk 几何改动有没有把答案改坏
#   36 题、greedy、reasoning_effort=none、max_tokens 64（与 W804 §7 同一套）
#   两臂的 prefill 都是确定性的（W805c：B∥C 逐字节相同）=> 每臂一条即可
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w805d_task_$STAMP.txt
MAXT=64
WANT_ENV=12
N_TASK=$(python3 -c "import json;print(len(json.load(open('task_corpus.json'))['tasks']))")
cp "$CFG" /tmp/w805d_prod.json
restore_cfg() {
  cp /tmp/w805d_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W805d task gate chunk A=auto(8192) B=auto:16384  $STAMP tasks=$N_TASK max_tokens=$MAXT" > "$OUT"
python3 -c "import hashlib;b=open('task_corpus.json','rb').read();print('  corpus sha16=%s'%hashlib.sha256(b).hexdigest()[:16])" >> "$OUT"

setarm() {   # $1 = A|B
  python3 - "$CFG" "$1" <<'EOP'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
a = list(d.get("args") or [])
while "--prefill" in a:
    i = a.index("--prefill")
    del a[i:i + 2]
a += ["--prefill", "auto" if arm == "A" else "auto:16384"]
d["args"] = a
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
EOP
}

run() {
  local arm=$1
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s" >> "$OUT"
  local got ch
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  ch=$(grep -a "prompt chunk auto" "$LOG" | tail -1 | cut -c1-60)
  echo "  ENVCHECK want=$WANT_ENV got=${got:-?} :: ${ch:-?}" >> "$OUT"
  if [ "${got:-0}" != "$WANT_ENV" ]; then echo "!! ABORT env_n $got" >> "$OUT"; exit 1; fi
  python3 mt_task.py 8090 "$arm" "$DATA/w805d_task_$arm.json" task_corpus.json "$MAXT" >> "$OUT" 2>&1
  [ -f "$DATA/w805d_task_$arm.json" ] || { echo "!! ABORT no JSON $arm" >> "$OUT"; exit 1; }
}

run A
run B
echo "== DONE $OUT"
