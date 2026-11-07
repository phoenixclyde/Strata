#!/bin/sh
# 通用单臂脚本：arm_run.sh NAME [K V]...   （V=__DEL__ 表示删除该 env）
# 自恢复：无论正常结束还是 HUP/INT/TERM，都会 cp 回原 config 并重启生产。
set -u
NAME=${1:-arm}
shift || true
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/arm_${NAME}_$TS.txt
BAK=$CFG.bak_${NAME}_$TS
CONT=strata166-407
MODEL=qwen3.8-flash-next-ud-iq4_xs-abliterated

restore() {
  echo "=== RESTORE $(date +%H:%M:%S) ===" >> "$OUT"
  cp -f "$BAK" "$CFG" && echo "config restored" >> "$OUT"
  md5sum "$CFG" >> "$OUT"
  docker restart "$CONT" >/dev/null 2>&1 && echo "container restarted" >> "$OUT"
  for i in $(seq 1 150); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "prod ready ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
}

echo "ARM=$NAME START $(date +%Y-%m-%d_%H:%M:%S)" > "$OUT"
cp -f "$CFG" "$BAK"
md5sum "$CFG" >> "$OUT"
echo "governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)" >> "$OUT"
echo "overrides=$*" >> "$OUT"

python3 - "$CFG" "$@" >> "$OUT" 2>&1 <<'PY'
import json, sys
p = sys.argv[1]
pairs = sys.argv[2:]
d = json.load(open(p))
e = d.setdefault('env', {})
for i in range(0, len(pairs) - 1, 2):
    k, v = pairs[i], pairs[i + 1]
    if v == '__DEL__':
        e.pop(k, None)
    else:
        e[k] = v
e['STRATA_DECODE_TIMING'] = '1'
e['STRATA_VERIFY_PROFILE'] = '1'
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print('env_now', e)
PY

trap 'restore' EXIT HUP INT TERM

docker restart "$CONT" >/dev/null 2>&1
for i in $(seq 1 150); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
  sleep 1
done
sleep 25
for i in $(seq 1 12); do
  code=$(curl -s --max-time 30 -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8090/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"warm\"}],\"max_tokens\":4,\"temperature\":0}")
  if [ "$code" = "200" ]; then echo "warmup ok (try $i)" >> "$OUT"; break; fi
  echo "warmup http=$code" >> "$OUT"
  sleep 6
done

# 记录该臂的 slots（HC_Q8 会影响专家槽位，是判据之一）
curl -s --max-time 10 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1

prev_s=$(grep -a -c "decode GPU stages" "$LOG")
prev_t=$(grep -a -c "decode timing" "$LOG")
# 两次丢弃：重启后专家缓存要几轮才填满（R0 实测前 2-4 个请求偏高约 3%）
for i in d1 d2; do
  echo "--- DISCARD $i $(date +%H:%M:%S) ---" >> "$OUT"
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  prev_s=$(grep -a -c "decode GPU stages" "$LOG")
  prev_t=$(grep -a -c "decode timing" "$LOG")
done
for i in 1 2 3; do
  echo "--- RUN $i $(date +%H:%M:%S) ---" >> "$OUT"
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  now_s=$(grep -a -c "decode GPU stages" "$LOG")
  now_t=$(grep -a -c "decode timing" "$LOG")
  [ "$now_s" -gt "$prev_s" ] && grep -a "decode GPU stages" "$LOG" | tail -n +$((prev_s + 1)) >> "$OUT"
  [ "$now_t" -gt "$prev_t" ] && grep -a "decode timing" "$LOG" | tail -n +$((prev_t + 1)) >> "$OUT"
  prev_s=$now_s
  prev_t=$now_t
done
echo "ARM_DONE $(date +%H:%M:%S)" >> "$OUT"
