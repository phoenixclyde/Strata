#!/bin/bash
C=strata166-407
echo "=== [1] md5: host src028 vs container /src ==="
md5sum /home/albus/strata166/src028/serve/web/app.css
docker exec $C bash -lc 'md5sum /src/serve/web/app.css' 2>&1
echo
echo "=== [2] what the browser ACTUALLY gets over HTTP ==="
curl -s --max-time 8 http://127.0.0.1:8090/web/app.css | grep -nE "^\.(monitor|about|chat)[ ,{]" | head -5
echo "--- bytes served vs on-disk ---"
curl -s --max-time 8 http://127.0.0.1:8090/web/app.css | wc -c
wc -c < /home/albus/strata166/src028/serve/web/app.css
echo
echo "=== [3] index.html monitor section (grid) ==="
curl -s --max-time 8 http://127.0.0.1:8090/ | grep -nE "view--monitor|monitor-row|st-metric" | head -12
echo
echo "=== [4] container mounts (can we hot-fix without rebuild?) ==="
docker inspect $C --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}}){{println}}{{end}}' 2>&1
echo
echo "=== [5] does the container copy web into image or read host? ==="
docker exec $C bash -lc 'ls -la /src/serve/web/app.css; readlink -f /src/serve/web/app.css'
