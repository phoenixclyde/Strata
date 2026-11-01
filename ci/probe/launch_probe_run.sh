#!/usr/bin/env bash
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
docker run --rm --device=/dev/kfd --device=/dev/dri -v "$HERE":/w -w /w \
  strata-gfx906:0.2.9-101 bash -lc 'hipcc --offload-arch=gfx906 -O3 -o launch_probe launch_probe.cpp 2>&1 | head -20 && echo "--- built ---" && ./launch_probe'
