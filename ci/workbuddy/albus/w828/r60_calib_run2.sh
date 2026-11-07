set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
c=json.loads(json.dumps(base))
c['exe']='/data/bin/strata-0.1.54n'
c['log']='/data/w828_calib2.log'
json.dump(c, open('/home/albus/strata166/data/w828_calib2.json','w'), ensure_ascii=False, indent=1)
print('run2 cfg exe', c['exe'], 'args', len(c['args']), 'env', len(c['env']))
PY
timeout 90 docker stop -t 25 strata166-407 >/dev/null 2>&1 && echo "prod stopped" || echo "stop failed"
sleep 3
for x in $(docker ps -aq --filter "name=w828"); do docker rm -f "$x" >/dev/null 2>&1; done
rm -f /home/albus/strata166/data/w828_calib2.out
docker run -d --name w828calib2 --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/src028:/src -v /home/albus/strata166/data:/data \
  -v /models:/models:ro \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  -w /src strata-gfx906:0.2.8 \
  bash -lc 'python3 tools/calibrate.py /data/w828_calib2.json > /data/w828_calib2.out 2>&1; echo EXIT=$? >> /data/w828_calib2.out' >/dev/null
sleep 20
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep w828calib2 || echo "CALIB2 GONE"
tail -6 /home/albus/strata166/data/w828_calib2.out 2>/dev/null | cut -c1-170
