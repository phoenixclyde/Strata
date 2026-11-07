#!/bin/sh
# W798e：decode 第二批三个开关（A 基线 + GDN_SPLIT / TSUM / QFUSE）
# 上一批结论：Q8_PACKED / EXPERT_V2 生效但方向反（VRAM hits +37.7%），LFUSE 相位全平。
# 本批 GDN_SPLIT 与 W797 已见效的 GDN 同族（rec -50%），最可能正向。 **按相位判**（规则 P 的 decode 侧用法）
#
# 为什么换口径：W798 的端到端 decode 测不出东西 ——
#   v1（6 轮都问"数数字"）：轮次越后 draft 越准，decode_ms 单调降 4062->3482->3198（27% 假趋势）
#   v2（6 轮问题各异）：轮间不可比（数数字 4376 vs 解释概念 5464，+35%）
#   => 端到端 decode 的单位置噪声 7-17%，低于要测的效应量级。
# 改法：STRATA_VERIFY_PROFILE=1 的 `decode GPU stages (ms/window)` 是 GPU 事件计时，
#   分项直接对应各开关的作用点（VRAM hits = 专家流 / shared+quant / waitA-B = launch 与流重叠 /
#   q8+qkv gemv = MMVQ）。每臂 4 轮 × 每轮一条 => 12 个相位样本。
# 注意：profiler 会关掉 SH_STREAM 的 fork（源码逐字「The profiler turns the fork off」），故 B 臂不进本轮。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w798e_phase_$TS.txt
BAK=$CFG.bak_w798e_$TS
CONT=strata166-407
OKFLAG=/tmp/w798e_done
ARMS="A B C D"
rm -f "$OKFLAG"

set_env() {
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
drop = ('STRATA_GDN_SPLIT', 'STRATA_TSUM', 'STRATA_QFUSE', 'STRATA_VERIFY_PROFILE')
e = {k: v for k, v in d.get('env', {}).items() if k not in drop}
if arm != 'PROD':
    e['STRATA_VERIFY_PROFILE'] = '1'
if arm == 'B': e['STRATA_GDN_SPLIT'] = '1'
if arm == 'C': e['STRATA_TSUM'] = '1'
if arm == 'D': e['STRATA_QFUSE'] = '1'

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
trap 'keepup' EXIT HUP INT TERM

for arm in $ARMS; do
  echo "=== ARM $arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_env "$arm"
  restart_up
  curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'])" >> "$OUT" 2>&1
  prev=$(grep -a -c "decode GPU stages" "$LOG")
  python3 /home/albus/strata166/tmp/mt_phase.py >> "$OUT" 2>&1
  now=$(grep -a -c "decode GPU stages" "$LOG")
  if [ "$now" -gt "$prev" ]; then
    grep -a "decode GPU stages" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"
  fi
done

echo "=== RESTORE PROD $(date +%H:%M:%S) ===" >> "$OUT"
set_env PROD
restart_up
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "env_final=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
