#!/bin/bash
# W802-B（P3）：STRATA_PREFILL_CPU_SHARE 0 vs auto，在 read 100-350 的真实 chat 区间
#   机理：把「只被少数 token 路由到」的专家交给空闲 CPU 池，省掉它们的 PCIe 拷贝 => 打 wait copy
#   两臂都开 STRATA_PREFILL_TIMING=1（公平），判据：wait copy 相位 + TTFT
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w802b_cpushare_$STAMP.txt
cp "$CFG" "$CFG.bak_w802b_$STAMP"
cp "$CFG" /tmp/w802b_prod.json
echo "# W802b cpu_share 0 vs auto  $STAMP  order=A B B A A B  chat 80,280,80,280 gen64" > "$OUT"

setcs() {   # $1 = 0 | auto   （两臂都开 PREFILL_TIMING）
  cp /tmp/w802b_prod.json "$CFG"
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, val = sys.argv[1], sys.argv[2]
d = json.load(open(cfg)); e = d.setdefault("env", {})
e["STRATA_PREFILL_CPU_SHARE"] = val
e["STRATA_PREFILL_TIMING"] = "1"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  setcs share=%s env_n=%d" % (val, len(e)))
PY
}

run() {
  local val=$1 arm=$2 rep=$3
  setcs "$val"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm share=$val rep $rep ready=${ok}s" >> "$OUT"
  snap "$OUT"
  python3 mt_chat.py 80,280,80,280 64 >> "$OUT" 2>&1
  slice "$OUT" "strata prefill timing: [0-9]+ tokens"
}

run 0    A 1
run auto B 1
run auto B 2
run 0    A 2
run 0    A 3
run auto B 3

cp /tmp/w802b_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
