#!/bin/sh
# W799：多轮「每轮 park 一整份 KV snapshot」的地板 —— 测 --conversation-cache-park-gain
#
# 已定位（干净状态、重启后）：
#   每轮 `conversation cache: parked 7589 tokens in 222.9 ms; snapshot_bytes=330210608`（写 RAM）
#   + 下一轮读回 => 实测地板 read=46 时 prompt_ms ~918-1000 ms，斜率 ~1.8 ms/token
#   源码注释逐字（generate.cpp:12744）：「re-parking writes the whole snapshot only for the next turn to drop it again」
#   => `--conversation-cache-park-gain N`：本轮比上次 park 时进步不足 N token 就不 park（N=0 默认=每轮都 park）
#
# 本参数只改「何时 park」，不改任何计算 => 位一致、无质量风险，判据只看时间（不需要 needle）。
# 臂：A=0（现状） B=256 C=1024。每臂重启 -> mt_floor（6 个 read 点：46/108/237/529/1008/1954）。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w799_gain_$TS.txt
BAK=$CFG.bak_w799_$TS
CONT=strata166-407
OKFLAG=/tmp/w799_done
rm -f "$OKFLAG"

set_gain() {   # $1 = 0|256|1024
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, g = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
a = d.get('args') or []
a = [x for x in a if x != '--conversation-cache-park-gain']
# 值要紧跟参数：先剔除孤立的旧值
if '--conversation-cache-park-gain' in a:
    i = a.index('--conversation-cache-park-gain'); a.pop(i)
if g != '0':
    a += ['--conversation-cache-park-gain', g]
d['args'] = a
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('gain', g, 'tail_args', a[-6:])
PY
}

restart_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 300); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 6
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restore $(date +%H:%M:%S) ===" >> "$OUT"
    set_gain 0; restart_up
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK"
echo "bak=$BAK image=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"
trap 'keepup' EXIT HUP INT TERM

for g in 0 256 1024; do
  echo "=== GAIN $g $(date +%H:%M:%S) ===" >> "$OUT"
  set_gain "$g"
  restart_up
  prev=$(grep -ac "conversation cache:" "$LOG")
  python3 /home/albus/strata166/tmp/mt_floor.py >> "$OUT" 2>&1
  now=$(grep -ac "conversation cache:" "$LOG")
  echo "park_lines=$((now-prev))" >> "$OUT"
  if [ "$now" -gt "$prev" ]; then
    grep -a "conversation cache:" "$LOG" | tail -n +$((prev + 1)) | cut -c1-170 >> "$OUT"
  fi
done

echo "=== RESTORE gain=0 $(date +%H:%M:%S) ===" >> "$OUT"
set_gain 0
restart_up
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "args_tail=$(python3 -c "import json;print(json.load(open('$CFG')).get('args')[-4:])")" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
