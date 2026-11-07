#!/bin/bash
# Build the existing source tree against llama.cpp b12129 in a SEPARATE build dir.
# build-r28 (the release build, 3cf0325) is not touched: a failed experiment must not
# leave the releasable tree half-configured.
set -uo pipefail
SRC_R=/home/albus/strata166/pr/strata-fork
OLD=/home/albus/strata166/build-r28
NEW=/home/albus/strata166/build-lcpp
LC=/home/albus/strata166/ref/llama_b12129

if [ ! -d "$NEW" ]; then
  cp -a "$OLD" "$NEW" || { echo COPY_FAIL; exit 3; }
fi
cd "$NEW" || exit 3
# objects from 3cf0325 must not survive: a link that reuses them is a mixed binary
find . -name '*.o' -delete 2>/dev/null
find . -name '*.a' -delete 2>/dev/null
rm -f strata

echo "=== reconfigure with STRATA_GGML_DIR=$LC"
cmake -DSTRATA_GGML_DIR="$LC" . > /tmp/cmake_b12129.log 2>&1
echo "cmake rc=$?"
tail -5 /tmp/cmake_b12129.log

echo "=== ninja -j6 strata (background log /tmp/ninja_b12129.log)"
ninja -j6 strata > /tmp/ninja_b12129.log 2>&1
echo "ninja rc=$?"
grep -c "error:" /tmp/ninja_b12129.log 2>/dev/null
tail -20 /tmp/ninja_b12129.log
