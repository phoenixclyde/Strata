#!/usr/bin/env bash
# [W863 R30] Build and run the controlled read probe (zero downtime: reads a scratch buffer).
set -u
DIR=/home/albus/strata166/ci/probe
mkdir -p "$DIR"
echo "=== compile ==="
docker run --rm --device=/dev/kfd --device=/dev/dri \
  -v "$DIR":/work -w /work strata-gfx906:0.2.9-101 \
  bash -c 'hipcc --offload-arch=gfx906 -O3 -o read_probe read_probe.cpp 2>&1 | tail -6; ls -l read_probe' 2>&1 | tail -8
echo
echo "=== run ==="
docker run --rm --device=/dev/kfd --device=/dev/dri \
  -v "$DIR":/work -w /work strata-gfx906:0.2.9-101 \
  bash -c './read_probe' 2>&1 | tail -40
