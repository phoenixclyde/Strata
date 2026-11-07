#!/bin/bash
# W863 · 增量重编：只让 ninja 跳过 build.ninja 重生成（缺 /llama.cpp 挂载，见 d7），
# 编译/归档/链接全部由 ninja 自己执行，不手抄任何 flag。
set -u
S=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
IMG=strata-gfx906:0.2.9-101

echo "=== build.ninja md5 BEFORE ==="
md5sum "$B/build.ninja"
echo "=== stale objects count (would all be rebuilt if we forced a full build) ==="
find "$B" -name "*.o" -newer "$B/strata" | wc -l

docker rm -f w863build >/dev/null 2>&1
docker run -d --name w863build --security-opt label=disable \
  -v "$S":/src -v "$B":/out "$IMG" \
  bash -lc 'cd /out && touch build.ninja && md5sum build.ninja && ninja strata; echo "NINJA_RC=$?"; md5sum build.ninja' 2>&1 | tail -1
sleep 10
docker inspect w863build --format 'status={{.State.Status}}' 2>/dev/null
docker logs w863build 2>&1 | tail -8
