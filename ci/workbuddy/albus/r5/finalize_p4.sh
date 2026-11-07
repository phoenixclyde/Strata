#!/bin/sh
# W794 收尾：装最终 env（生产 6 项 + swizzle）、needle 门、逐位一致性（swizzle 开/关各跑一条定长贪婪）、
# 最后停在"swizzle 开"的生产态。
set -u
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
CONT=strata166-407
OUT=/home/albus/strata166/data/w794_final_$(date +%Y%m%d_%H%M%S).txt
OK=/tmp/w794_final_ok
rm -f "$OK"

set_env() {   # $1 = on|off
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, mode = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
e = {k: v for k, v in d.get('env', {}).items()
     if k not in ('STRATA_PREFILL_TIMING', 'STRATA_GFX906_ATTN_QUERY_SWIZZLE', 'STRATA_GFX906_ATTN_REDUCE12')}
if mode == 'on':
    e['STRATA_GFX906_ATTN_QUERY_SWIZZLE'] = '1'
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('env', sorted(e.items()))
PY
}

up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 240); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 8
}

det() {   # 定长贪婪输出 → 哈希（content + reasoning_content 一起）
  python3 - >> "$OUT" 2>&1 <<'PY'
import json, urllib.request, hashlib
body = {"model": "qwen3.8-flash-next-ud-iq4_xs-abliterated",
        "messages": [{"role": "user", "content": "请只回答两个字：好的"}],
        "max_tokens": 8, "temperature": 0}
req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                             data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=600) as r:
    m = json.loads(r.read().decode())["choices"][0]["message"]
txt = (m.get("content") or "") + "|" + (m.get("reasoning_content") or "")
print("det_sha16=%s len=%d c=%r" % (hashlib.sha256(txt.encode()).hexdigest()[:16], len(txt), (m.get("content") or "")[:24]))
PY
}

echo "START $(date +%H:%M:%S)" > "$OUT"
cp -f "$CFG" "$CFG.bak_w794final_$(date +%H%M%S)"
echo "=== swizzle ON ===" >> "$OUT"
set_env on; up
docker exec "$CONT" python3 /src/tools/needle_bench.py --lengths 32k --depths 50 --url http://127.0.0.1:8090 >> "$OUT" 2>&1
det
echo "=== swizzle OFF (identity probe) ===" >> "$OUT"
set_env off; up
det
echo "=== back to ON ===" >> "$OUT"
set_env on; up
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "image=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"
echo "env_final=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
touch "$OK"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
