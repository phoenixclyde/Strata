#!/bin/bash
# W802e：CPU share 的质量门（第一半）—— needle 32k 深度 10/50/90，两臂各一次
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w802e_needle_$STAMP.txt
cp "$CFG" "$CFG.bak_w802e_$STAMP"
cp "$CFG" /tmp/w802e_prod.json
echo "# W802e needle 32k d10/50/90  share=0 vs auto  $STAMP" > "$OUT"
setcs() {
  cp /tmp/w802e_prod.json "$CFG"
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, val = sys.argv[1], sys.argv[2]
d = json.load(open(cfg)); e = d.setdefault("env", {})
e["STRATA_PREFILL_CPU_SHARE"] = val
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
}
run() {
  setcs "$1"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "=== NEEDLE share=$1 $(date +%H:%M:%S) ===" >> "$OUT"
  docker exec strata166-407 python3 /src/tools/needle_bench.py --lengths 32k --depths 10,50,90 --url http://127.0.0.1:8090 2>&1 | tail -6 >> "$OUT"
}
run 0
run auto
cp /tmp/w802e_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
