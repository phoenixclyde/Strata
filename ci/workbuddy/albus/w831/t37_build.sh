#!/bin/bash
S=/home/albus/strata166/src028
set -e
echo "=== build strata-gfx906:0.2.8p2 (adds the W831 monitor-width fix) ==="
date +%H:%M:%S
docker build -q -t strata-gfx906:0.2.8p2 -f $S/Dockerfile.w828 $S 2>&1 | tail -3
date +%H:%M:%S
echo
echo "=== verify the patched css is inside the image ==="
docker run --rm strata-gfx906:0.2.8p2 bash -lc 'md5sum /src/serve/web/app.css; grep -c "ALBUS-W831" /src/serve/web/app.css; tail -3 /src/serve/web/app.css'
echo
echo "=== old image still there for rollback ==="
docker images | grep -E "strata-gfx906 +(0.2.8|0.2.8p1|0.2.8p2)" | head -5
