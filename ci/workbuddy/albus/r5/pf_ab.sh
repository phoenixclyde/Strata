#!/bin/sh
# R5-prefill A/B: STRATA_HIP_PROMPT_F16=1（FP16 prompt GEMM）在 gfx906 上的效果。
# 序列 B F B F（各臂 2 个 M 请求，均带 PREFILL_TIMING=1）；needle 只在第二轮的 B/F 各跑一次。
# 自恢复：任何退出路径都 cp 回原 config 并重启生产（纪律⑥ 远端 detached）。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/r5_ab_$TS.txt
BAK=$CFG.bak_r5ab_$TS
CONT=strata166-407

restore() {
  echo "=== RESTORE $(date +%H:%M:%S) ===" >> "$OUT"
  cp -f "$BAK" "$CFG" && echo "config restored" >> "$OUT"
  md5sum "$CFG" >> "$OUT"
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 200); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "prod ready ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('after slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
  echo "env_after=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
  echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
}

set_env() {   # $1 = 0/1 for STRATA_HIP_PROMPT_F16
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
p, v = sys.argv[1], sys.argv[2]
d = json.load(open(p))
e = d.setdefault('env', {})
e['STRATA_PREFILL_TIMING'] = '1'
e['STRATA_HIP_PROMPT_F16'] = v
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print('env_now', sorted(e.items()))
PY
}

wait_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 200); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 20
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK"
md5sum "$CFG" >> "$OUT"
echo "governor=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c | tr '\n' ' ')" >> "$OUT"

trap 'restore' EXIT HUP INT TERM

round=0
for arm in B F B F; do
  round=$((round + 1))
  echo "=== ARM $arm round $round $(date +%H:%M:%S) ===" >> "$OUT"
  if [ "$arm" = "B" ]; then set_env 0; else set_env 1; fi
  wait_up
  prev=$(grep -a -c "strata prefill timing" "$LOG")
  for r in 1 2; do
    echo "--- $arm run$r ---" >> "$OUT"
    python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
    now=$(grep -a -c "strata prefill timing" "$LOG")
    if [ "$now" -gt "$prev" ]; then
      grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"
    fi
    prev=$now
  done
  if [ "$round" -ge 3 ]; then
    echo "--- $arm needle 32k d10,d90 ---" >> "$OUT"
    docker exec "$CONT" python3 /src/tools/needle_bench.py --lengths 32k --depths 10,90 \
      --url http://127.0.0.1:8090 >> "$OUT" 2>&1
  fi
done

echo "DONE $(date +%H:%M:%S)" >> "$OUT"
