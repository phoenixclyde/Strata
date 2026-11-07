#!/bin/bash
set -u
C=strata166-407
echo "=== 1) 运行件与配置 ==="
docker exec $C sh -lc 'P=$(pgrep -f "strata-0.1.56 --serve" | head -1); echo pid=$P; md5sum /proc/$P/exe | cut -c1-32; grep VmLck /proc/$P/status; tr "\0" "\n" < /proc/$P/environ | grep -c INJECT'
docker exec $C sh -lc 'python3 -c "import json;d=json.load(open(\"/data/strata-huihui-ud-iq4_xs.json\"));print(\"exe=\",d[\"exe\"]);print(\"env=\",len(d[\"env\"]),\"args=\",len(d[\"args\"]))"'

echo
echo "=== 2) 启动关键行（0.2.10 的变化） ==="
docker exec $C sh -lc 'grep -nE "PLE table|expert cache [0-9]+ slots|borrows [0-9]+|prompt chunk auto|window up to" /data/strata-huihui-ud-iq4_xs.log | tail -8' | cut -c1-170

echo
echo "=== 3) 新出现的 warning / error（本次启动之后） ==="
docker exec $C sh -lc 'awk "/engine started: \/data\/bin\/strata-0.1.56/{f=1} f" /data/strata-huihui-ud-iq4_xs.log | grep -iE "warn|error|ERR |fail" | head -10' | cut -c1-170
echo "(空 = 无)"

echo
echo "=== 4) health 细节 ==="
curl -s -m 5 http://127.0.0.1:8090/health | head -c 200; echo
docker inspect -f 'restarts={{.RestartCount}} started={{.State.StartedAt}}' $C
