#!/bin/bash
# Same as try_build.sh, but inside the build image: cmake/ninja only exist there.
# The mount point stays /llama.cpp so build-lcpp's cache stays identical to the release
# build's; only the content behind it changes (b12129 instead of 3cf0325).
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
NEW=/home/albus/strata166/build-lcpp
LC=/home/albus/strata166/ref/llama_b12129

[ -d "$NEW" ] || cp -a /home/albus/strata166/build-r28 "$NEW"

docker run --rm --security-opt label=disable \
  -v "$R":/src -v "$NEW":/out -v "$LC":/llama.cpp \
  strata-gfx906:0.2.11-101 bash -lc '
set -uo pipefail
cd /out
find . -name "*.o" -delete 2>/dev/null
find . -name "*.a" -delete 2>/dev/null
rm -f strata
echo "=== cmake"
cmake -DSTRATA_GGML_DIR=/llama.cpp . > /tmp/cm.log 2>&1
echo "cmake rc=$?"; tail -4 /tmp/cm.log
echo "=== ninja -j6 strata"
ninja -j6 strata > /tmp/nj.log 2>&1
echo "ninja rc=$?"
echo "errors=$(grep -c "error:" /tmp/nj.log 2>/dev/null || echo 0)"
grep "error:" /tmp/nj.log | head -10
tail -8 /tmp/nj.log
ls -l strata 2>/dev/null && md5sum strata 2>/dev/null
' 2>&1 | tail -30
