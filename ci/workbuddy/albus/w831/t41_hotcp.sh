#!/bin/bash
C=strata166-407
F=/home/albus/strata166/src028/serve/web/app.js
echo "=== host md5 ==="
md5sum $F; wc -c < $F
echo
echo "=== hot-copy into the running container (no restart) ==="
docker cp $F $C:/src/serve/web/app.js
docker exec $C bash -lc 'md5sum /src/serve/web/app.js; grep -c "ALBUS-W831" /src/serve/web/app.js'
echo
echo "=== what the browser gets now ==="
curl -s --max-time 8 http://127.0.0.1:8090/web/app.js | md5sum
curl -s --max-time 8 http://127.0.0.1:8090/web/app.js | grep -c "ALBUS-W831"
echo
echo "=== engine still alive ==="
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 120
