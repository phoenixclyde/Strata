#!/bin/sh
# W795：专家 MMQ 的三臂（env-only，同镜像 0.2.4p4，交错 A B C A B C）
#   A 基（MMQ 默认开）
#   B +STRATA_PREFILL_MMQ=0  —— FP16 专家路径（dequant 到 f16 + rocBLAS f16 GEMM）
#   C +STRATA_MMQ_GROUP_SORT=1
# 每臂：restart -> health -> 丢弃前 2 请求 -> M 档一次（相位账）。
# 收尾：把 env 恢复成生产 7 项（无 TIMING / 无 MMQ / 无 GROUP_SORT）再 restart。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w795_ab_$TS.txt
BAK=$CFG.bak_w795_$TS
CONT=strata166-407
OKFLAG=/tmp/w795_done
PROD="HSA_OVERRIDE_GFX_VERSION=9.0.6 STRATA_PREFILL_CPU_SHARE=0 STRATA_RESIDENT_HEADROOM_GIB=0.5 STRATA_HC_Q8=1 STRATA_HIP_PROMPT_F16=1 STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.5.0.txt STRATA_GFX906_ATTN_QUERY_SWIZZLE=1"

rm -f "$OKFLAG"

set_env() {   # $1 = A|B|C|PROD
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
drop = ('STRATA_PREFILL_TIMING', 'STRATA_PREFILL_MMQ', 'STRATA_MMQ_GROUP_SORT',
        'STRATA_MMQ_RESIDENT_SORT_NE', 'STRATA_MMQ_DIRECT')
e = {k: v for k, v in d.get('env', {}).items() if k not in drop}
if arm != 'PROD':
    e['STRATA_PREFILL_TIMING'] = '1'
if arm == 'B':
    e['STRATA_PREFILL_MMQ'] = '0'
if arm == 'C':
    e['STRATA_MMQ_GROUP_SORT'] = '1'
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('arm', arm, 'env', sorted(e.items()))
PY
}

restart_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 240); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 6
}

# 丢掉重启后的前 2 个请求（协议：重启丢前 2 请求）
warm2() {
  python3 - >> "$OUT" 2>&1 <<'PY'
import json, urllib.request
for i in range(2):
    body = {"model": "qwen3.8-flash-next-ud-iq4_xs-abliterated",
            "messages": [{"role": "user", "content": "回复一个字：好"}], "max_tokens": 4, "temperature": 0}
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            r.read()
        print("warm %d ok" % i)
    except Exception as ex:
        print("warm %d FAIL %r" % (i, ex))
PY
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restore prod env $(date +%H:%M:%S) ===" >> "$OUT"
    set_env PROD
    restart_up
    curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'])" >> "$OUT" 2>&1
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK"
echo "bak=$BAK" >> "$OUT"
echo "image=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"
echo "gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)" >> "$OUT"

trap 'keepup' EXIT HUP INT TERM

for arm in A B C A B C; do
  echo "=== ARM $arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_env "$arm"
  restart_up
  grep -a "prompt chunk auto" "$LOG" | tail -1 >> "$OUT"
  grep -a -E "MMQ reads|MMQ sorts|no tile for" "$LOG" | tail -2 >> "$OUT"
  warm2
  prev=$(grep -a -c "strata prefill timing" "$LOG")
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  now=$(grep -a -c "strata prefill timing" "$LOG")
  if [ "$now" -gt "$prev" ]; then grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"; fi
  grep -a -E "^strata serve: prompt .* tokens =" "$LOG" | tail -1 >> "$OUT"
done

echo "=== RESTORE PROD $(date +%H:%M:%S) ===" >> "$OUT"
set_env PROD
restart_up
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "env_final=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
