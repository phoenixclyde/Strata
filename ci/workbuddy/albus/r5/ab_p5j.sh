#!/bin/sh
# W795b：MMQ 瓦片宽度 J 的上限扫描（p5 镜像）
#   臂 = 0(不设 = 上游启发式，实测 J=64) / 48 / 24 / 8 / 40
# 前置：把生产容器从 p4 换到 p5（旧容器改名 .bak_w795 保留）；换镜失败即回滚。
# 每臂：restart -> health -> 丢前 2 请求 -> M 档一次（相位账）+ 引擎打印的 "MMQ tile:" 行（实际选中的 J）。
# 判据：gemm gate/up + gemm down 两个相位（其余相位与 J 无关，当对照）。
# 收尾：env 恢复生产 7 项并 restart。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w795j_ab_$TS.txt
BAK=$CFG.bak_w795j_$TS
CONT=strata166-407
IMG=strata-gfx906:0.2.4p5
OKFLAG=/tmp/w795j_done
ARMS="0 48 24 8 40"

rm -f "$OKFLAG"

set_env() {   # $1 = J 上限 | PROD
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, j = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
drop = ('STRATA_PREFILL_TIMING', 'STRATA_PREFILL_MMQ', 'STRATA_MMQ_GROUP_SORT',
        'STRATA_MMQ_TILE_J', 'STRATA_MMQ_TILE_LOG')
e = {k: v for k, v in d.get('env', {}).items() if k not in drop}
if j != 'PROD':
    e['STRATA_PREFILL_TIMING'] = '1'
    e['STRATA_MMQ_TILE_LOG'] = '1'
    if j != '0':
        e['STRATA_MMQ_TILE_J'] = j
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('J', j, 'env', sorted(e.items()))
PY
}

up() {
  for i in $(seq 1 300); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 6
}

restart_up() { docker restart "$CONT" >/dev/null 2>&1; up; }

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
echo "bak=$BAK" >> "$OUT"
echo "gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)" >> "$OUT"
echo "image_before=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"

# ---- 换镜像 p4 -> p5（失败即回滚）----
if [ "$(docker inspect -f '{{.Config.Image}}' $CONT)" != "$IMG" ]; then
  docker stop -t 30 "$CONT" >/dev/null 2>&1
  docker rename "$CONT" "${CONT}.bak_w795" >/dev/null 2>&1
  docker run -d --name "$CONT" \
    --device /dev/kfd --device /dev/dri \
    -v /models:/models:ro -v /home/albus/strata166/data:/data \
    -p 8090:8090 --network bridge --ipc host --group-add video \
    --restart unless-stopped \
    "$IMG" /bin/bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
  up
  if ! curl -s --max-time 3 http://127.0.0.1:8090/health >/dev/null 2>&1; then
    echo "=== SWAP FAILED: rollback $(date +%H:%M:%S) ===" >> "$OUT"
    docker logs --tail 40 "$CONT" >> "$OUT" 2>&1
    docker rm -f "$CONT" >/dev/null 2>&1
    docker rename "${CONT}.bak_w795" "$CONT" >/dev/null 2>&1
    docker start "$CONT" >/dev/null 2>&1
    up
    touch "$OKFLAG"
    echo "ROLLED_BACK" >> "$OUT"
    exit 0
  fi
fi
echo "image_after=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"

trap 'keepup' EXIT HUP INT TERM

for j in $ARMS; do
  echo "=== J=$j $(date +%H:%M:%S) ===" >> "$OUT"
  set_env "$j"
  restart_up
  grep -a "MMQ tile:" "$LOG" | tail -4 >> "$OUT"
  grep -a "prompt chunk auto" "$LOG" | tail -1 >> "$OUT"
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
echo "image_final=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
