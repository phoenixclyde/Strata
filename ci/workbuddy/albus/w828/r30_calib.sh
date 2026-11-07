set -e
cd /home/albus/strata166
python3 - <<'PY'
import json, hashlib
src='/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
c=json.load(open(src))
c['exe']='/data/bin/strata-0.1.54n'
c['log']='/data/w828_calib.log'
p='/home/albus/strata166/data/w828_calib.json'
json.dump(c, open(p,'w'), ensure_ascii=False, indent=1)
json.dump(c, open('/home/albus/strata166/data/w828_calib_orig.json','w'), ensure_ascii=False, indent=1)
print('calib cfg exe:', c['exe'], 'args', len(c['args']), 'env', len(c['env']))
print('prod md5', hashlib.md5(open(src,'rb').read()).hexdigest()[:16])
PY
timeout 90 docker stop -t 25 strata166-407 >/dev/null 2>&1 && echo "production stopped" || echo "stop failed"
sleep 3
docker rm -f w828calib >/dev/null 2>&1 || true
docker run -d --name w828calib --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/src028:/src -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  -w /src strata-gfx906:0.2.8 \
  bash -lc 'python3 tools/calibrate.py /data/w828_calib.json > /data/w828_calib.out 2>&1; echo EXIT=$? >> /data/w828_calib.out' >/dev/null
sleep 12
docker ps --format '{{.Names}} {{.Status}}' | grep w828calib || echo "CALIB GONE"
tail -12 /home/albus/strata166/data/w828_calib.out 2>/dev/null || echo "(no output yet)"
