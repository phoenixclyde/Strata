#!/bin/bash
# W933 B 臂：切回 auto(8192) 测部分前缀复用
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
"
docker restart strata166-407
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done
$C sh -c "grep -E 'prompt chunk auto' /data/strata-huihui-ud-iq4_xs.log | tail -1"
