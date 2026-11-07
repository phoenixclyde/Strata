#!/bin/sh
# W797：gfx906 从不继承 arch_default_env（只有 gfx12/gfx1151 有表）=> 上游 20 个 S23/S25/S26 优化
#       在我们这张卡上默认全关、从未测过。本轮测落在 GDN 那 22.5% 上的五个。
#
# 先验（不是推断）：
#   `gfx906_gdn_rec_head` 单测（tests/hip/gdn_rec_head.cpp）已在 gfx906 上编好跑过：
#   variant 1（quad，= STRATA_GDN_HEAD=1）对 variant 0，全部 7 个 T（7/8/9/17/100/2048/2051）
#   **y16 与 state 逐位相等（d16=0, dsn=0），FAILURES: 0**；T=2048 上 4.561 vs 7.589 ms = 1.66x。
#   => HEAD 是「逐位安全」的，上游没给 gfx906 设默认不是因为它错，而是因为只看过 gfx1151。
#
# 臂：
#   A 基（生产 8 项 env + TIMING）
#   B +STRATA_GDN_HEAD=1            靶 `gdn recurrence`（M 7.0%）
#   C +HEAD=1 +STRATA_GDN_PP=2      靶同上（gfx1151 默认值；单测未覆盖 PP，靠 needle 兜）
#   D +HEAD=1 +STRATA_GDN_NOY=1     靶同上（省 403 MB/chunk 的 FP32 死写；y 不属于契约）
#   E +STRATA_GDN_CONVL2=1          靶 `gdn`（conv + L2 norm 合一；纯逐列循环，无 warp 假设）
#
# 判据（规则 P）：先看相位 —— HEAD/PP/NOY 只该动 `gdn recurrence`，CONVL2 只该动 `gdn`；其余相位必须不动。
# 收尾：env 恢复生产 8 项并 restart。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w797_ab_$TS.txt
BAK=$CFG.bak_w797_$TS
CONT=strata166-407
OKFLAG=/tmp/w797_done
ARMS="A B C D E"

rm -f "$OKFLAG"

set_env() {   # $1 = A|B|C|D|E|PROD
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
drop = ('STRATA_PREFILL_TIMING', 'STRATA_GDN_HEAD', 'STRATA_GDN_PP',
        'STRATA_GDN_NOY', 'STRATA_GDN_CONVL2')
e = {k: v for k, v in d.get('env', {}).items() if k not in drop}
if arm != 'PROD':
    e['STRATA_PREFILL_TIMING'] = '1'
if arm in ('B', 'C', 'D'):
    e['STRATA_GDN_HEAD'] = '1'
if arm == 'C':
    e['STRATA_GDN_PP'] = '2'
if arm == 'D':
    e['STRATA_GDN_NOY'] = '1'
if arm == 'E':
    e['STRATA_GDN_CONVL2'] = '1'
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('arm', arm, 'env', sorted(e.items()))
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

warm2() {
  python3 - >> "$OUT" 2>&1 <<'PY'
import json, urllib.request
for i in range(2):
    body = {"model": "qwen3.8-flash-next-ud-iq4_xs-abliterated",
            "messages": [{"role": "user", "content": "回复一个字：好"}], "max_tokens": 4, "temperature": 0}
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r: r.read()
    except Exception as ex:
        print("warm %d FAIL %r" % (i, ex))
PY
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restore $(date +%H:%M:%S) ===" >> "$OUT"
    set_env PROD; restart_up
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK"
echo "bak=$BAK image=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"
echo "gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)" >> "$OUT"

trap 'keepup' EXIT HUP INT TERM

for arm in $ARMS; do
  echo "=== ARM $arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_env "$arm"
  restart_up
  warm2
  for prof in M L; do
    prev=$(grep -a -c "strata prefill timing" "$LOG")
    python3 /home/albus/strata166/tmp/w776_bench.py $prof 1 >> "$OUT" 2>&1
    now=$(grep -a -c "strata prefill timing" "$LOG")
    if [ "$now" -gt "$prev" ]; then grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"; fi
  done
  if [ "$arm" != "A" ] && [ "$arm" != "E" ]; then
    echo "--- needle ($arm) ---" >> "$OUT"
    docker exec "$CONT" python3 /src/tools/needle_bench.py --lengths 32k --depths 50 --url http://127.0.0.1:8090 >> "$OUT" 2>&1
  fi
done

echo "=== RESTORE PROD $(date +%H:%M:%S) ===" >> "$OUT"
set_env PROD
restart_up
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "env_final=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
