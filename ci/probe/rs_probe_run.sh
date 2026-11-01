#!/usr/bin/env bash
# Build and run the R x S interaction probe inside the production image.
# Read-only against the GPU, <=360 MiB, safe to run next to the live service.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
IMG=strata-gfx906:0.2.9-101

docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  -v "$HERE":/w -w /w \
  "$IMG" bash -lc '
    set -e
    hipcc --offload-arch=gfx906 -O3 -o rs_probe rs_probe.cpp 2>&1 | tail -5
    echo "--- built ---"
    ./rs_probe '"${1:-}"'
  '
