#!/bin/bash
set -u
cd /home/albus/strata166
docker run --rm \
  -v /home/albus/strata166/work/r90-080:/src \
  -v /home/albus/strata166/build-070:/out \
  -v /home/albus/strata166/ref/llama_b10700:/ref \
  -v /home/albus/strata166/data:/data \
  -w /out strata-gfx906:0.2.10-101 \
  bash -lc 'nice -n 10 ninja -j6 strata > /data/w962/b070.log 2>&1; echo RC=$?; grep -c "error:" /data/w962/b070.log || true; tail -3 /data/w962/b070.log'
