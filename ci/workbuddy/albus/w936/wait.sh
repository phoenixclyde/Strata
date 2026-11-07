#!/bin/bash
set -u
C=strata166-407
for i in $(seq 1 80); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done
echo
echo "=== 引擎指纹 ==="
docker exec $C sh -lc 'P=$(pgrep -f "strata-0.1.55t --serve" | head -1); echo pid=$P; md5sum /proc/$P/exe | cut -c1-32; tr "\0" "\n" < /proc/$P/environ | grep -E "INJECT_FATAL" | sort'
echo
echo "=== server.py 指纹 ==="
docker exec $C md5sum /src/serve/server.py
echo
echo "=== 启动日志关键行 ==="
docker exec $C sh -lc 'grep -inE "PLE table|expert cache [0-9]+ slots|fatal GPU|engine started" /data/strata-huihui-ud-iq4_xs.log | tail -6' | cut -c1-150
echo
echo "=== 注入标志文件应不存在 ==="
docker exec $C sh -lc 'ls -l /data/w936/fired.flag 2>&1 | head -1'
