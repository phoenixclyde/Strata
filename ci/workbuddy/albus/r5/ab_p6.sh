#!/bin/sh
# W796：两个"已实现但从未正确测过"的注意力/选择器开关，按新规则 P（相位判）
#   A 基
#   B +STRATA_SELECT_SIMT=1   靶 `qsa select`（M 2.1% / L 6.9%）。W793 曾在 M 上判 -0.36%=噪声否决，
#                             但从未在 L 上测（上游在 RDNA2 128K 报该相位 2.71->0.587 ms）
#   C +STRATA_ATTN_LANECELL=1 靶 `qsa attn`（M 19.5% / L 15.3%）。源码注释：scores 逐位一致、无 shuffle 归约
# 每臂：restart -> 丢前 2 请求 -> M 1 -> L 1 -> needle 32k@50%。判据看相位（M/L 各一行 `strata prefill timing`）。
# 收尾：env 恢复生产 7 项并 restart。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w796_ab_$TS.txt
BAK=$CFG.bak_w796_$TS
CONT=strata166-407
OKFLAG=/tmp/w796_done
ARMS="A B C"

rm -f "$OKFLAG"

set_env() {   # $1 = A|B|C|PROD
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
drop = ('STRATA_PREFILL_TIMING', 'STRATA_SELECT_SIMT', 'STRATA_ATTN_LANECELL')
e = {k: v for k, v in d.get('env', {}).items() if k not in drop}
if arm != 'PROD':
    e['STRATA_PREFILL_TIMING'] = '1'
if arm == 'B':
    e['STRATA_SELECT_SIMT'] = '1'
if arm == 'C':
    e['STRATA_ATTN_LANECELL'] = '1'
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('arm', arm, 'env', sorted(e.items()))
PY
}

restart_up() {
  . ./lib_a9.sh
  mark "$OUT"
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
  slice "$OUT" "qsa select:|attn-query-swizzle"   # AUDIT9 规则 U：marker 切片，不用全日志 tail
  warm2
  for prof in M L; do
    prev=$(grep -a -c "strata prefill timing" "$LOG")
    python3 /home/albus/strata166/tmp/w776_bench.py $prof 1 >> "$OUT" 2>&1
    now=$(grep -a -c "strata prefill timing" "$LOG")
    if [ "$now" -gt "$prev" ]; then grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"; fi
  done
  echo "--- needle ($arm) ---" >> "$OUT"
  docker exec "$CONT" python3 /src/tools/needle_bench.py --lengths 32k --depths 50 --url http://127.0.0.1:8090 >> "$OUT" 2>&1
done

echo "=== RESTORE PROD $(date +%H:%M:%S) ===" >> "$OUT"
set_env PROD
restart_up
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "env_final=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
