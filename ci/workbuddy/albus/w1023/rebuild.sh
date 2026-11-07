#!/bin/bash
# Incremental rebuild of build-lcpp against b12129, after the MMQ call-site port.
set -uo pipefail
docker run --rm --security-opt label=disable \
  -v /home/albus/strata166/pr/strata-fork:/src \
  -v /home/albus/strata166/build-lcpp:/out \
  -v /home/albus/strata166/ref/llama_b12129:/llama.cpp \
  strata-gfx906:0.2.11-101 bash -lc '
cd /out
ninja -j6 strata > /tmp/nj2.log 2>&1
rc=$?
echo "ninja rc=$rc"
echo "errors=$(grep -c "error:" /tmp/nj2.log)"
grep "error:" /tmp/nj2.log | head -12
tail -4 /tmp/nj2.log
ls -l strata 2>/dev/null
md5sum strata 2>/dev/null
'
