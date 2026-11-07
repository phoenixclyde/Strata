#!/bin/bash
# W1031 / R100-S1: full rebuild of the engine against llama.cpp v0.9.0 (b12110 / cd959ba).
# Same image, same cache values as the production build dir (build-r28), same mounts but
# STRATA_GGML_DIR (/llama.cpp) points at the v0.9.0 tree. Nothing is installed; the binary
# stays in build-v090/strata until the numeric and speed gates say otherwise.
set -u
IMG=strata-gfx906:0.2.11-101
SRC=/home/albus/strata166/pr/strata-fork
LL=/home/albus/strata166/ref/llama_b12110
OUT=/home/albus/strata166/build-v090
BASE=/home/albus/strata166/build-r28

mkdir -p "$OUT"
[ -f "$OUT/CMakeCache.txt" ] || cp "$BASE/CMakeCache.txt" "$OUT/CMakeCache.txt"
docker rm -f v090-build >/dev/null 2>&1

docker run --rm --name v090-build --device=/dev/kfd --device=/dev/dri \
  -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc '
set -u
cd /out
echo "=== cmake configure ==="
cmake -S /src -B /out -G Ninja > /out/_cmake.log 2>&1
rc=$?
echo "CMAKE_RC=$rc"
tail -25 /out/_cmake.log
[ "$rc" -ne 0 ] && exit "$rc"
echo "=== ninja -j12 strata ==="
date +%s > /out/_t0
ninja -j12 strata > /out/_ninja.log 2>&1
rc=$?
date +%s > /out/_t1
echo "NINJA_RC=$rc  elapsed=$(( $(cat /out/_t1) - $(cat /out/_t0) ))s"
tail -40 /out/_ninja.log
ls -l /out/strata 2>/dev/null
md5sum /out/strata 2>/dev/null
exit "$rc"'
