set -e
cd /home/albus/strata166
pkill -f w828_ab.sh 2>/dev/null || true
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker rm -f strata166-407 >/dev/null 2>&1 || true
docker run -d --name strata166-407 --restart unless-stopped \
  --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  strata-gfx906:0.2.8p2 bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
sleep 10
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
python3 -c "
import json;c=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
print('prod exe:',c['exe'],'args',len(c['args']),'env',len(c['env']))
"
