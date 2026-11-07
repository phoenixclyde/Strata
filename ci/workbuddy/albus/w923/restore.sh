#!/bin/bash
set -u
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 恢复配置（去掉全部 profiler env）==="
docker exec strata166-407 cp ${CFG}.bak-w923 $CFG
docker exec strata166-407 md5sum $CFG
docker exec strata166-407 python3 -c "
import json
d=json.load(open('$CFG'))
print('env count:', len(d['env']))
print('profiler left:', [k for k in d['env'] if k.startswith('ROCPROF') or k=='HSA_TOOLS_LIB'])
"

echo
echo "=== 重启并等 health ==="
docker restart strata166-407 >/dev/null && echo RESTARTED
for i in $(seq 1 120); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo
echo "=== 验证 ==="
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); echo -n "engine: "; md5sum /proc/$P/exe|cut -c1-32; echo -n "profiler env: "; tr "\0" "\n" < /proc/$P/environ | grep -cE "ROCPROF|HSA_TOOLS_LIB"'
docker exec strata166-407 sh -c "tail -200 /data/strata-huihui-ud-iq4_xs.log | grep -E 'expert cache [0-9]+ slots|borrows|VRAM free' | tail -3 | cut -c1-130"
docker inspect -f 'restarts={{.RestartCount}}' strata166-407
