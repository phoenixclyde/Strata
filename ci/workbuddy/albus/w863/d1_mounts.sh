#!/bin/bash
echo "=== container mounts ==="
docker inspect strata166-407 --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} (rw={{.RW}}){{"\n"}}{{end}}'
echo "=== does the engine binary live on the host? ==="
ls -la /home/albus/strata166/data/bin/ | head -20
echo "=== binary identity ==="
md5sum /home/albus/strata166/data/bin/strata-0.1.55g 2>/dev/null
docker exec strata166-407 md5sum /data/bin/strata-0.1.55g 2>/dev/null
echo "=== image id / size ==="
docker images strata-gfx906 --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | head -5
echo "=== build tree state (gfx029-build) ==="
ls -la /home/albus/strata166/gfx029-build/strata 2>/dev/null || ls /home/albus/strata166/gfx029-build/ | head -20
echo "=== is the build tree configured from pr/strata-fork? ==="
grep -m2 "CMAKE_HOME_DIRECTORY\|/src" /home/albus/strata166/gfx029-build/CMakeCache.txt 2>/dev/null | head -5
