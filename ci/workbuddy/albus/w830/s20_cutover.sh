set -e
D=/home/albus/strata166/data
CFG=$D/strata-huihui-ud-iq4_xs.json
cd /home/albus/strata166
cp -a "$CFG" "$CFG.bak-w830-cutover"
python3 - "$CFG" <<'PY'
import io, json, sys
p = sys.argv[1]
c = json.load(io.open(p, encoding='utf-8'))
old = c['exe']
c['exe'] = '/data/bin/strata-0.1.54n2'
io.open(p, 'w', encoding='utf-8').write(json.dumps(c, ensure_ascii=False, indent=1) + '\n')
print('exe:', old, '->', c['exe'], '| args', len(c['args']), '| env', len(c['env']))
PY
docker rm -f strata166-407 >/dev/null 2>&1 || true
docker run -d --name strata166-407 --restart unless-stopped \
  --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v "$D":/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  strata-gfx906:0.2.8p1 bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
sleep 10
docker ps --format '{{.Names}} {{.Status}} {{.Image}}' | grep strata166
echo "--- waiting for health ---"
for i in $(seq 1 480); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "READY=${i}s"; break; }
  sleep 1
done
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 160; echo
echo "--- startup lines of this boot (rocBLAS / prefill / cache) ---"
docker logs strata166-407 2>&1 | grep -aiE "rocblas|prompt chunk|expert cache|PROMPT_F16|0\.1\.54" | tail -8 | cut -c1-190
