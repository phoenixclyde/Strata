#!/bin/sh
# W794：p4 镜像（= p3 + gfx906 注意力布局置换放开到 k8v4）三臂，交错 A B C A B C。
#   A 基 / B +STRATA_GFX906_ATTN_QUERY_SWIZZLE=1 / C + 同上 +REDUCE12=1
# 每臂：M 档一次（相位账）+ 一条定长贪婪输出（哈希，用于验证"逐位一致"）。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w794_ab_$TS.txt
BAK=$CFG.bak_w794_$TS
CONT=strata166-407
OKFLAG=/tmp/w794_done

rm -f "$OKFLAG"

set_env() {
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
drop = ('STRATA_PREFILL_TIMING', 'STRATA_GFX906_ATTN_QUERY_SWIZZLE', 'STRATA_GFX906_ATTN_REDUCE12')
e = {k: v for k, v in d.get('env', {}).items() if k not in drop}
e['STRATA_PREFILL_TIMING'] = '1'
if arm in ('B', 'C'):
    e['STRATA_GFX906_ATTN_QUERY_SWIZZLE'] = '1'
if arm == 'C':
    e['STRATA_GFX906_ATTN_REDUCE12'] = '1'
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
  sleep 8
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restart $(date +%H:%M:%S) ===" >> "$OUT"
    restart_up
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK"
echo "bak=$BAK" >> "$OUT"
echo "image=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"

trap 'keepup' EXIT HUP INT TERM

# 换镜像（p3 -> p4），保留旧容器
echo "=== swap to p4 $(date +%H:%M:%S) ===" >> "$OUT"
docker rm -f "$CONT.bak_w794" >/dev/null 2>&1
docker rename "$CONT" "$CONT.bak_w794" >> "$OUT" 2>&1
docker run -d --name "$CONT" \
  --device /dev/kfd --device /dev/dri \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  -p 8090:8090 --network bridge --ipc host --group-add video \
  --restart unless-stopped \
  strata-gfx906:0.2.4p4 /bin/bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
echo "new_container=$(docker inspect -f '{{.Config.Image}}' $CONT 2>/dev/null)" >> "$OUT"
up=0
for i in $(seq 1 240); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { up=1; echo "p4 healthy ${i}s" >> "$OUT"; break; }
  sleep 1
done
if [ "$up" = "0" ]; then
  echo "=== P4 DID NOT COME UP: rollback ===" >> "$OUT"
  docker logs --tail 30 "$CONT" >> "$OUT" 2>&1
  docker rm -f "$CONT" >> "$OUT" 2>&1
  docker rename "$CONT.bak_w794" "$CONT" >> "$OUT" 2>&1
  docker start "$CONT" >> "$OUT" 2>&1
  touch "$OKFLAG"; echo "ROLLED_BACK" >> "$OUT"; exit 0
fi

for arm in A B C A B C; do
  echo "=== ARM $arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_env "$arm"
  restart_up
  prev=$(grep -a -c "strata prefill timing" "$LOG")
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  now=$(grep -a -c "strata prefill timing" "$LOG")
  if [ "$now" -gt "$prev" ]; then grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"; fi
  grep -a "attn-query-swizzle\|attn-reduce12" "$LOG" | tail -1 >> "$OUT"
  # 逐位一致性：定长贪婪输出取哈希
  python3 - "$OUT" <<'PY' >> "$OUT" 2>&1
import json, sys, urllib.request, hashlib
body = {"model": "qwen3.8-flash-next-ud-iq4_xs-abliterated",
        "messages": [{"role": "user", "content": "用三句话解释什么是梯度的下降方向，不要用公式。"}],
        "max_tokens": 48, "temperature": 0}
req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                             data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=600) as r:
    txt = json.loads(r.read().decode())["choices"][0]["message"]["content"]
print("det_out_sha16=%s len=%d" % (hashlib.sha256(txt.encode()).hexdigest()[:16], len(txt)))
PY
done

touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
