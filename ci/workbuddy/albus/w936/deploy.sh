#!/bin/bash
set -u
B=/home/albus/strata166/gfx029-build
W=/home/albus/strata166/work/r77
C=strata166-407

echo "=== 0) 确认容器身份与 /src 可写 ==="
docker exec $C id
docker exec $C sh -lc 'touch /src/.w936_probe 2>&1 && echo "/src WRITABLE" && rm -f /src/.w936_probe || echo "/src READ-ONLY"'

echo
echo "=== 1) 备份（落 /data，bind mount 持久） ==="
docker exec $C mkdir -p /data/w936
docker exec $C sh -lc 'cp /src/serve/server.py /data/w936/server.py.bak && md5sum /data/w936/server.py.bak'
docker exec $C sh -lc 'cp /data/strata-huihui-ud-iq4_xs.json /data/strata-huihui-ud-iq4_xs.json.bak_w936 && echo cfg-bak-ok'
docker exec $C sh -lc 'ls -l /data/bin/strata-0.1.55t | awk "{print \$5}"'

echo
echo "=== 2) 换二进制（新 inode + 旧件改名保留） ==="
docker cp $B/strata $C:/data/bin/strata-0.1.55t.new >/dev/null 2>&1
docker exec $C sh -lc 'chmod +x /data/bin/strata-0.1.55t.new && mv /data/bin/strata-0.1.55t /data/bin/strata.bak-8e92c662 && mv /data/bin/strata-0.1.55t.new /data/bin/strata-0.1.55t && md5sum /data/bin/strata-0.1.55t'

echo
echo "=== 3) 打 server.py ==="
docker cp $W/serve/server.py $C:/src/serve/server.py.new >/dev/null 2>&1
docker exec $C sh -lc 'mv /src/serve/server.py.new /src/serve/server.py && md5sum /src/serve/server.py'
echo "--- 期望 cf2ba243 ==="

echo
echo "=== 4) 加注入 env（测试钩子） ==="
docker exec $C python3 -c "
import json
p='/data/strata-huihui-ud-iq4_xs.json'
d=json.load(open(p))
d['env']['STRATA_INJECT_FATAL']='2'
d['env']['STRATA_INJECT_FATAL_ONCE']='/data/w936/fired.flag'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('env keys:', len(d['env']))
print('INJECT:', d['env']['STRATA_INJECT_FATAL'], d['env']['STRATA_INJECT_FATAL_ONCE'])
"

echo
echo "=== 5) 重启 ==="
docker restart $C >/dev/null 2>&1 && echo RESTARTED
