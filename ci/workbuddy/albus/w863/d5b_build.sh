#!/bin/bash
set -u
S=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
IMG=strata-gfx906:0.2.9-101
docker rm -f w863build >/dev/null 2>&1
# gfx029-build was configured as /src -> /out; mount it at /out so ninja's VerifyGlobs resolves
docker run -d --name w863build --security-opt label=disable \
  -v "$S":/src -v "$B":/out "$IMG" \
  bash -lc 'cd /out && ninja strata; echo "NINJA_RC=$?"' 2>&1 | tail -1
sleep 8
docker inspect w863build --format 'status={{.State.Status}} exit={{.State.ExitCode}}' 2>/dev/null
docker logs w863build 2>&1 | tail -6
