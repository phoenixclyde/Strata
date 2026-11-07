#!/bin/bash
set -u
B=/home/albus/strata166/build-r28/strata
C=strata166-407

echo "=== 修前 ==="
docker exec $C sh -lc 'md5sum /data/bin/strata-0.1.56 | cut -c1-32; stat -c%s /data/bin/strata-0.1.56'

echo
echo "=== 从构建物恢复（cp -> .new -> mv，换 inode） ==="
docker cp "$B" $C:/data/bin/strata-0.1.56.new >/dev/null 2>&1
docker exec $C sh -lc 'chmod 755 /data/bin/strata-0.1.56.new && mv -f /data/bin/strata-0.1.56.new /data/bin/strata-0.1.56 && echo restored'

echo
echo "=== 修后：磁盘 / 构建物 / 运行件 三方比对 ==="
echo -n "disk    : "; docker exec $C sh -lc 'md5sum /data/bin/strata-0.1.56 | cut -c1-32; stat -c%s /data/bin/strata-0.1.56'
echo -n "build   : "; md5sum $B | cut -c1-32; stat -c%s $B
echo -n "running : "; docker exec $C sh -lc 'P=$(pgrep -f "strata-0.1.56 --serve"|head -1); md5sum /proc/$P/exe | cut -c1-32'

echo
echo "=== 服务未受影响确认 ==="
curl -s -m 5 http://127.0.0.1:8090/health | head -c 80; echo
docker inspect -f 'restarts={{.RestartCount}}' $C
