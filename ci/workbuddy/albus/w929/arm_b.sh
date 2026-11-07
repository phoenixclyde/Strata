#!/bin/bash
# W929 B 臂：--kv int8 (=k8v8) + 同样的 STRATA_PREFILL_TIMING
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 1. 改 --kv k8v4 -> int8 ==="
$C python3 -c "
import json
p='$CFG'
d=json.load(open(p))
i=d['args'].index('--kv')
old=d['args'][i+1]
d['args'][i+1]='int8'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('kv: %s -> %s' % (old, d['args'][i+1]))
print('env count =', len(d['env']))
"

echo "=== 2. 重启 ==="
docker restart strata166-407
echo "=== 3. 等健康 ==="
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo "=== 4. 关键布局（槽数是否被 KV 抢） ==="
$C sh -c "grep -E 'expert cache [0-9]+ slots|VRAM free with everything|borrows [0-9]+ CUDA0' /data/strata-huihui-ud-iq4_xs.log | tail -3"
$C sh -c "tr '\0' ' ' < /proc/\$(pgrep -f 'strata-0.1.55t --serve'|head -1)/cmdline | grep -o '\-\-kv [a-z0-9_]*'"
echo "=== 5. KV 模式确认（日志） ==="
$C sh -c "grep -inE 'kv.*int8|int8.*kv|hybrid|k8v4' /data/strata-huihui-ud-iq4_xs.log | tail -3" | cut -c1-170
