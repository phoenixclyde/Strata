#!/bin/bash
# W801b-fix：chat 口径 PROD(11 env) vs BASE7(7 env)
# 修上一版的 bug：saved 文件在第二次 BASE7 时把自己写成 {}，导致后面的 PROD 臂实际跑的是 BASE7 环境。
# 现在改为「开跑前留一份 PROD 原件」+ 每臂断言 env_n（11/7），不符立即中止。
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w801c_chat_$STAMP.txt
DROP="STRATA_GDN_HEAD STRATA_GDN_PP STRATA_SELECT_SIMT STRATA_ROUTE_TAIL_SKIP"
cp "$CFG" "$CFG.bak_w801c_$STAMP"
cp "$CFG" /tmp/w801c_prod.json          # PROD 原件（只写一次，之后只读）
echo "# W801c chat PROD(11) vs BASE7(7)  $STAMP  order=A B B A A B" > "$OUT"
python3 -c "import json;print('start env_n=%d'%len(json.load(open('$CFG'))['env']))" >> "$OUT"

setarm() {   # $1=PROD|BASE7
  if [ "$1" = "PROD" ]; then
    cp /tmp/w801c_prod.json "$CFG"
  else
    python3 - "$CFG" "$DROP" <<'PY'
import json, sys
cfg, drop = sys.argv[1], sys.argv[2].split()
d = json.load(open(cfg)); e = dict(d.get("env") or {})
for k in drop: e.pop(k, None)
d["env"] = e
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
  fi
  python3 -c "import json;print('  setarm $1 env_n=%d'%len(json.load(open('$CFG'))['env']))" >> "$OUT"
}

run() {
  local arm=$1 rep=$2 want=$3
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm rep $rep ready=${ok}s (want env_n=$want)" >> "$OUT"
  snap "$OUT"
  local got
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  echo "  ENVCHECK want=$want got=${got:-?}" >> "$OUT"
  if [ "${got:-0}" != "$want" ]; then echo "!! ABORT: env_n mismatch" >> "$OUT"; echo "ABORT env_n $got != $want"; exit 1; fi
  python3 mt_chat.py 80,280,80,280 64 >> "$OUT" 2>&1
  slice "$OUT" "conversation cache: parked"
}

run PROD  1 11
run BASE7 1 7
run BASE7 2 7
run PROD  2 11
run PROD  3 11
run BASE7 3 7

cp /tmp/w801c_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;print('final env_n=%d'%len(json.load(open('$CFG'))['env']))" >> "$OUT"
echo "== DONE $OUT"
