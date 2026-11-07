#!/bin/bash
set -u
C=strata166-407

echo "=== 1) 持久化 server.py 补丁副本（容器重建后要用） ==="
docker exec $C sh -lc 'cp /src/serve/server.py /data/w936/server.py.r77 && cp /src/serve/test_fatal_gpu_restart.py /data/w936/test_fatal_gpu_restart.py.r77 && md5sum /data/w936/server.py.r77'

echo
echo "=== 2) 移除注入 env ==="
docker exec $C python3 -c "
import json
p='/data/strata-huihui-ud-iq4_xs.json'
d=json.load(open(p))
for k in ('STRATA_INJECT_FATAL','STRATA_INJECT_FATAL_ONCE'):
    d['env'].pop(k, None)
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('env keys:', len(d['env']))
print('remaining:', ','.join(sorted(d['env'])))
"

echo
echo "=== 3) 重启 ==="
docker restart $C >/dev/null 2>&1 && echo RESTARTED
