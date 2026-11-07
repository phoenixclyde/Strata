#!/bin/bash
C=strata166-407
echo "=== container / image / uptime ==="
docker ps --format '{{.Names}} | {{.Status}}' | grep strata166
docker inspect $C --format 'image={{.Config.Image}}'
echo
echo "=== engine config untouched? ==="
python3 -c "
import json
c=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
print('exe:',c['exe'])
print('args:',len(c['args']),' env:',len(c['env']))
print('spec args:',[a for a in c['args'] if 'spec' in a or 'pcie' in a])
"
echo
echo "=== health ==="
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 200; echo
echo
echo "=== rollback inventory ==="
docker images | grep strata-gfx906 | head -4
ls -la /home/albus/strata166/src028/serve/web/app.css.bak-w831 /home/albus/strata166/src028/serve/web/app.js.bak-w831b 2>&1
ls -la /home/albus/strata166/data/bin/ | grep -E "strata-0.1.54n" | head -3
echo
echo "=== 4-way md5 (css/js) ==="
for f in app.css app.js; do
  echo "  $f tree      $(md5sum /home/albus/strata166/src028/serve/web/$f | cut -d' ' -f1)"
  echo "  $f image     $(docker run --rm strata-gfx906:0.2.8p2 bash -lc "md5sum /src/serve/web/$f" | cut -d' ' -f1)"
  echo "  $f container $(docker exec $C md5sum /src/serve/web/$f | cut -d' ' -f1)"
  echo "  $f served    $(curl -s --max-time 6 http://127.0.0.1:8090/web/$f | md5sum | cut -d' ' -f1)"
done
