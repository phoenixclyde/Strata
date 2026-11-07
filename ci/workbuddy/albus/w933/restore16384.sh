#!/bin/bash
# W933：恢复 auto:16384（R76 判定：部分前缀场景仅 0.4%，代价 0.04 s/请求）
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json

$C python3 -c "
import json
p='$CFG'
d=json.load(open(p))
i=d['args'].index('--prefill')
old=d['args'][i+1]
d['args'][i+1]='auto:16384'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('  prefill: %s -> auto:16384' % old)
print('  args =', len(d['args']), ' env =', len(d['env']))
"
docker restart strata166-407
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done
echo "=== 最终状态 ==="
$C sh -c "grep -E 'prompt chunk auto|borrows [0-9]+ CUDA0|expert cache [0-9]+ slots' /data/strata-huihui-ud-iq4_xs.log | tail -3"
$C md5sum $CFG
$C md5sum /data/bin/strata-0.1.55t
