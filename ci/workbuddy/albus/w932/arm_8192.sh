#!/bin/bash
# W932 B 臂：只把 --prefill 从 auto:16384 改回 auto（8192），补丁与二进制都不动
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json

$C python3 -c "
import json
p='$CFG'
d=json.load(open(p))
i=d['args'].index('--prefill')
old=d['args'][i+1]
d['args'][i+1]='auto'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('  prefill: %s -> auto' % old)
print('  env count =', len(d['env']))
print('  binary unchanged (9d9cbe17)')
"
docker restart strata166-407
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done
echo "=== 布局（chunk 8192 + 三补丁 ⇒ borrows 应约 1226） ==="
$C sh -c "grep -E 'prompt chunk auto|borrows [0-9]+ CUDA0|expert cache [0-9]+ slots' /data/strata-huihui-ud-iq4_xs.log | tail -3"
