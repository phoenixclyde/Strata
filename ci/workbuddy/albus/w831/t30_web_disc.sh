#!/bin/bash
C=strata166-407
echo "=== [1] web root inside container ==="
docker exec $C bash -lc 'ls -la /data/web 2>/dev/null | head -20; echo ---; ls -la /app/web 2>/dev/null | head -20' 2>&1 | head -40
echo
echo "=== [2] locate app.js / static assets ==="
docker exec $C bash -lc 'find / -xdev -name "app.js" -not -path "*/node_modules/*" 2>/dev/null | head -10; echo ---css---; find / -xdev -name "*.css" -not -path "*/node_modules/*" 2>/dev/null | head -10' 2>&1 | head -30
echo
echo "=== [3] host-side copies ==="
ls -la /home/albus/strata166/src028/serve/web/ 2>&1 | head -20
echo "--- patches dir ---"
ls -la /home/albus/strata166/patches/ 2>&1 | head -30
