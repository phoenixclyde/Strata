#!/bin/sh
# W798：decode 侧 10 个开关里的 4 个（gfx1151 默认开、gfx906 从未测；上游「no bit-changing switch」黑名单里没有它们）
#
# 规则 K 的答案（本脚本第 0 步已量）：多轮场景 reused 99.8%，第 2 轮端到端 decode 占 83%、第 3-6 轮占 64-69%。
# 所以 decode 才是多轮的主项，与单轮 M 档"decode 只占 15%"完全不同的结论。
#
# 基准口径：8K prompt 建会话 -> 6 次追加（max_tokens=256）-> 取第 4-6 轮 decode_ms 的中位。
# 噪声：同一会话 4 轮的 decode_tok_s 极差 7.7%（71.0-76.5），故判据取 **>5%**，且每臂 3 个样本取中位。
#
# 臂（每臂只加一个开关，独立 restart）：
#   A 基（生产 10 项 env）
#   B +STRATA_SH_STREAM=1    shared expert 独占流，上游 decode +1.8% / +6.7%
#   C +STRATA_Q8_PACKED=1    Q8_0 的 packed 解码布局，上游 decode +2.3%（会多一份拷贝，注意 vram）
#   D +STRATA_EXPERT_V2=1    分组 decode 专家（IQ3_S gate/up + IQ4_NL down）
#   E +STRATA_LFUSE=1        共享专家与 KV append 周围的少 launch
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w798_ab_$TS.txt
BAK=$CFG.bak_w798_$TS
CONT=strata166-407
OKFLAG=/tmp/w798_done
ARMS="A B C D E"

rm -f "$OKFLAG"

set_env() {   # $1 = A|B|C|D|E|PROD
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
drop = ('STRATA_SH_STREAM', 'STRATA_Q8_PACKED', 'STRATA_EXPERT_V2', 'STRATA_LFUSE')
e = {k: v for k, v in d.get('env', {}).items() if k not in drop}
if arm == 'B': e['STRATA_SH_STREAM'] = '1'
if arm == 'C': e['STRATA_Q8_PACKED'] = '1'
if arm == 'D': e['STRATA_EXPERT_V2'] = '1'
if arm == 'E': e['STRATA_LFUSE'] = '1'
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
  # 关键词：packed 会打印拷贝量；shared stream 会打印 fork 状态
  slice "$OUT" "native dense: STRATA_Q8_PACKED|shared expert on its own stream|EXPERT_V2|lfuse"   # AUDIT9 规则 U
  curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'])" >> "$OUT" 2>&1
  python3 /home/albus/strata166/tmp/mt_decode.py 2>&1 | tail -14 >> "$OUT"
done

echo "=== RESTORE PROD $(date +%H:%M:%S) ===" >> "$OUT"
set_env PROD
restart_up
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "env_final=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
