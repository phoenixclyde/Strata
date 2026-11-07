set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
c=json.loads(json.dumps(base))
c['exe']='/data/bin/strata-0.1.54w'
c['log']='/data/w828_b154w16.log'
c['parallel']=16
json.dump(c, open('/home/albus/strata166/data/w828_b154w16.json','w'), ensure_ascii=False, indent=1)
print('cfg exe',c['exe'],'parallel',c['parallel'],'args',len(c['args']))
PY
timeout 90 docker stop -t 25 strata166-407 >/dev/null 2>&1 && echo "prod stopped" || echo "stop failed"
sleep 3
for x in $(docker ps -aq --filter "name=w828"); do docker rm -f "$x" >/dev/null 2>&1; done
docker run -d --name w828w16 --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  strata-gfx906:0.2.8 bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/w828_b154w16.json --port 8090' >/dev/null
sleep 15
docker ps --format '{{.Names}} {{.Status}}' | grep w828w16 || { echo GONE; docker logs w828w16 2>&1|tail -12|cut -c1-170; exit 3; }
docker logs w828w16 2>&1 | tail -8 | cut -c1-170
