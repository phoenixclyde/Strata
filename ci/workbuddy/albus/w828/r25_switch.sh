set -e
cd /home/albus/strata166
cp -a data/strata-huihui-ud-iq4_xs.json data/strata-huihui-ud-iq4_xs.json.bak-w828
python3 - <<'PY'
import json, hashlib
p='/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
c=json.load(open(p))
print('before exe:', c['exe'])
c['exe']='/data/bin/strata-0.1.54n'
json.dump(c, open(p,'w'), ensure_ascii=False, indent=1)
print('after  exe:', c['exe'], '| args', len(c['args']), '| env', len(c['env']))
print('md5', hashlib.md5(open(p,'rb').read()).hexdigest()[:16])
PY
docker rm -f w828b154n >/dev/null 2>&1 || true
docker rm -f strata166-407 >/dev/null 2>&1 || true
docker run -d --name strata166-407 --restart unless-stopped \
  --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  strata-gfx906:0.2.8 bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
sleep 10
docker ps --format '{{.Names}} {{.Status}}' | grep strata166 || { echo "CONTAINER GONE"; docker logs strata166-407 2>&1 | tail -12 | cut -c1-170; exit 3; }
docker logs strata166-407 2>&1 | tail -4 | cut -c1-160
