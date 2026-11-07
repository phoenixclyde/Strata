#!/bin/bash
# W802d：CPU share 的 parity（2 题 x 320 token，贪心），两臂各一次
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w802d_parity_$STAMP.txt
cp "$CFG" "$CFG.bak_w802d_$STAMP"
cp "$CFG" /tmp/w802d_prod.json
echo "# W802d parity $STAMP" > "$OUT"
setcs() {
  cp /tmp/w802d_prod.json "$CFG"
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
  echo "=== PARITY arm=$2 share=$1" >> "$OUT"
  python3 mt_parity.py "$2" >> "$OUT" 2>&1
}
run 0    S0
run auto SA
cp /tmp/w802d_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
