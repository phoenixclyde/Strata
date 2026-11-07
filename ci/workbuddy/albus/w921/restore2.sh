#!/bin/bash
set -u
BD=~/strata166/data/bin

echo "=== 用 mv 换 inode（cp 会 Text file busy）==="
mv $BD/strata-0.1.55t.bak-w921 $BD/strata-0.1.55t
md5sum $BD/strata-0.1.55t
ls -l $BD/strata-0.1.55t

echo "=== 重启切到新 inode ==="
docker restart strata166-407 >/dev/null && echo RESTARTED
for i in $(seq 1 84); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo
echo "=== 验证 ==="
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); echo -n "running md5: "; md5sum /proc/$P/exe | cut -c1-32; echo -n "disk md5: "; md5sum /data/bin/strata-0.1.55t | cut -c1-32'
docker inspect -f 'restarts={{.RestartCount}} ulimits={{json .HostConfig.Ulimits}}' strata166-407
