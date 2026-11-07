#!/bin/bash
set -u
BD=~/strata166/data/bin
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 1. 恢复二进制 a97f4479 ==="
cp -a $BD/strata-0.1.55t.bak-w921 $BD/strata-0.1.55t
md5sum $BD/strata-0.1.55t

echo "=== 2. 恢复 config（去三个 env）==="
docker exec strata166-407 cp ${CFG}.bak-w921 $CFG
docker exec strata166-407 python3 -c "
import json
d=json.load(open('$CFG'))
print('env count:', len(d['env']))
print('has PF_/ROUTED:', [k for k in d['env'] if 'PF_' in k or 'ROUTED' in k])
"
docker exec strata166-407 md5sum $CFG

echo "=== 3. 重启 ==="
docker restart strata166-407 >/dev/null && echo RESTARTED

echo "=== 4. 等 health ==="
for i in $(seq 1 84); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo
echo "=== 5. 验证恢复 ==="
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); md5sum /proc/$P/exe | cut -c1-32; tr "\0" "\n" < /proc/$P/environ | grep -cE "PF_GROUP|ROUTED|HC_REGION"'
docker exec strata166-407 sh -c "tail -300 /data/strata-huihui-ud-iq4_xs.log | grep -E 'borrows' | tail -1 | cut -c1-120"
