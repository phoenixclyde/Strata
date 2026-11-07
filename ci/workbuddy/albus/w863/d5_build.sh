#!/bin/bash
# W863 · 正式增量重编引擎，容器脱离运行（docker run -d），轮询用 d6_buildpoll.sh
set -u
S=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
IMG=strata-gfx906:0.2.9-101

cp -a "$B/CMakeCache.txt" "$B/CMakeCache.txt.w863pre" 2>/dev/null
echo "=== pre-build cache fingerprint ==="
md5sum "$B/CMakeCache.txt"
ls -l "$B/strata"

docker rm -f w863build >/dev/null 2>&1
docker run -d --name w863build --security-opt label=disable \
  -v "$S":/src -v "$B":/build "$IMG" \
  bash -lc 'cd /build && ninja strata; echo "NINJA_RC=$?"' 2>&1 | tail -2
sleep 5
docker inspect w863build --format 'status={{.State.Status}}' 2>/dev/null
