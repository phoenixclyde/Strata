#!/bin/bash
# W801：--conversation-cache-park-gain 0 vs 256 复测（AUDIT9 P1-1 的整改）
# 交错顺序 A B B A A B（抵消臂漂）；每臂：restart -> 环境快照 -> 8K 建会话 -> 4 档 read
# 取证纪律（AUDIT9 规则 U）：banner 与环境一律用「marker + tail -n +N0」和 /proc/<pid>/environ，不用全日志 tail
set -u
cd /home/albus/strata166/tmp || exit 1
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w801_gain_$STAMP.txt
CONT=strata166-407
cp "$CFG" "$CFG.bak_w801_$STAMP"
{
  echo "# W801 park-gain retest $STAMP  0 vs 256  4 sizes 46/237/529/1954  order=A B B A A B"
} > "$OUT"

snap() {   # 引擎进程实际 env（规则 U 第一档）
  echo "  envsnap(容器内):" >> "$OUT"
  docker exec "$CONT" bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_" | sort || echo NONE' 2>/dev/null | sed 's/^/    /' >> "$OUT"
  python3 -c "import json;a=json.load(open('$CFG')).get('args');print('  args_gain=%s' % [x for x in a if 'park-gain' in x or x=='256' or x=='0'])" >> "$OUT"
}

run_arm() {
  local arm=$1 rep=$2 val=$3
  python3 w801_setgain.py "$val" >> "$OUT" 2>&1
  docker restart "$CONT" >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 300); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }
    sleep 1
  done
  local n0
  n0=$(wc -l < "$LOG")
  echo "=== ARM $arm rep $rep ready=${ok}s val='$val' log0=$n0" >> "$OUT"
  snap
  python3 mt_gain.py 46,237,529,1954 >> "$OUT" 2>&1
  # 本臂新增的 park 行（marker 切片）
  tail -n +$((n0 + 1)) "$LOG" | grep -a "conversation cache: parked" | cut -c1-150 | sed 's/^/  PARK /' >> "$OUT"
}

run_arm A 1 0
run_arm B 1 256
run_arm B 2 256
run_arm A 2 0
run_arm A 3 0
run_arm B 3 256

python3 w801_setgain.py "" >> "$OUT" 2>&1
docker restart "$CONT" >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
