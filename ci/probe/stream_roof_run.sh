#!/usr/bin/env bash
# W863: measure the achievable read roof on the MI50 (the missing denominator).
set -u
HOST=/home/albus/strata166
DIR=$HOST/ci/probe
mkdir -p "$DIR"
echo "=== source ==="
ls -l "$DIR/stream_roof.cpp"

echo
echo "=== compile (gfx906) ==="
docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  -v "$DIR":/work -w /work \
  strata-gfx906:0.2.9-101 \
  bash -c 'hipcc --offload-arch=gfx906 -O3 -o stream_roof stream_roof.cpp 2>&1 | tail -5; ls -l stream_roof' \
  2>&1 | tail -8
rc=$?
echo "compile rc=$rc"

echo
echo "=== run ==="
docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  -v "$DIR":/work -w /work \
  strata-gfx906:0.2.9-101 \
  bash -c './stream_roof 384 20' 2>&1 | tail -60
