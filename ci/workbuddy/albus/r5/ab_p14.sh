#!/bin/bash
# W801b：今天这 11 项 env（PROD）vs 今天之前那 7 项（BASE7），在**多轮 chat 口径**上的差
#   PROD  = 11 项（含 GDN_HEAD/GDN_PP/SELECT_SIMT/RT_SKIP）
#   BASE7 = 去掉这 4 项（= 09:00 起点那套 env）
# 交错 A B B A（2 rep）；判据：每轮 prompt_ms（TTFT）与 decode_ms 的中位
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w801b_chat_$STAMP.txt
DROP="STRATA_GDN_HEAD STRATA_GDN_PP STRATA_SELECT_SIMT STRATA_ROUTE_TAIL_SKIP"
cp "$CFG" "$CFG.bak_w801b_$STAMP"
echo "# W801b chat 口径 $STAMP  PROD(11) vs BASE7(去掉 $DROP)  order=A B B A" > "$OUT"

setarm() {   # $1=PROD|BASE7
  python3 - "$CFG" "$1" "$DROP" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm, drop = sys.argv[1], sys.argv[2], sys.argv[3].split()
d = json.load(open(cfg)); e = dict(d.get("env") or {})
saved = "/tmp/w801b_saved.json"
if arm == "BASE7":
    json.dump({k: e[k] for k in drop if k in e}, open(saved, "w"))
    for k in drop: e.pop(k, None)
else:
    try:
        e.update(json.load(open(saved)))
    except Exception:
        pass
d["env"] = e
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("arm %s env_n=%d keys=%s" % (arm, len(e), sorted(e)))
PY
}

run() {
  local arm=$1 rep=$2
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm rep $rep ready=${ok}s" >> "$OUT"
  snap "$OUT"
  python3 mt_chat.py 80,280,80,280 64 >> "$OUT" 2>&1
  slice "$OUT" "conversation cache: parked"
}

run PROD 1
run BASE7 1
run BASE7 2
run PROD 2

setarm PROD
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
