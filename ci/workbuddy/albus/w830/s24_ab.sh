#!/bin/bash
# W830: A/B the restored binary (n2, with W793/W776) against the shipped one (n), same image, same config except exe.
set -u
DATA=/home/albus/strata166/data
SRC=$DATA/strata-huihui-ud-iq4_xs.json
python3 - "$SRC" <<'PY'
import json, copy
base = json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
for tag, exe in (('tn', '/data/bin/strata-0.1.54n'), ('tn2', '/data/bin/strata-0.1.54n2')):
    c = copy.deepcopy(base)
    c['exe'] = exe
    json.dump(c, open('/home/albus/strata166/data/w830_%s.json' % tag, 'w'), ensure_ascii=False, indent=1)
    print(tag, exe, 'nargs', len(c['args']), 'nenv', len(c['env']))
PY
for tag in tn tn2 tn2 tn; do
  echo "=== ARM $tag  $(date +%H:%M:%S)"
  docker rm -f "w830$tag" >/dev/null 2>&1
  timeout 90 docker stop -t 25 strata166-407 >/dev/null 2>&1
  sleep 2
  docker run -d --name "w830$tag" --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video -p 8090:8090 \
    -v /models:/models:ro -v "$DATA":/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    strata-gfx906:0.2.8p1 bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w830_$tag.json --port 8090" >/dev/null
  for i in $(seq 1 480); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  READY=${i}s"; break; }; sleep 1; done
  ( cd /home/albus/strata166/tmp && timeout 900 python3 w828_ttft3.py 8090 1200,2400,4800 2 3 2>&1 | tail -3 )
  docker rm -f "w830$tag" >/dev/null 2>&1
done
echo "=== restoring production ==="
bash /home/albus/strata166/tmp/r36_restore.sh
