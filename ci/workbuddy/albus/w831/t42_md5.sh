#!/bin/bash
C=strata166-407
F=/home/albus/strata166/src028/serve/web/app.js
echo "=== md5 across tree / image / container / served ==="
printf '  tree      %s\n' "$(md5sum $F | cut -d' ' -f1)"
printf '  image     %s\n' "$(docker run --rm strata-gfx906:0.2.8p2 bash -lc "md5sum /src/serve/web/app.js" | cut -d' ' -f1)"
printf '  container %s\n' "$(docker exec $C md5sum /src/serve/web/app.js | cut -d' ' -f1)"
printf '  served    %s\n' "$(curl -s --max-time 8 http://127.0.0.1:8090/web/app.js | md5sum | cut -d' ' -f1)"
echo
echo "=== markers in the image ==="
docker run --rm strata-gfx906:0.2.8p2 bash -lc 'grep -c "ALBUS-W831" /src/serve/web/app.js; grep -c "ALBUS-W831" /src/serve/web/app.css'
