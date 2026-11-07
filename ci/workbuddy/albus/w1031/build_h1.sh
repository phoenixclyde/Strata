#!/bin/bash
# H1: 0.9.0 + pin 的 Q8_1 修正和语义 → 构建（新树副本 llama_v090_h1，独立 build-h1）
set -u
IMG=strata-gfx906:0.2.11-101
SRC=/home/albus/strata166/w1031/src-v090
LL=/home/albus/strata166/w1031/llama_v090_h1
OUT=/home/albus/strata166/build-h1

if [ ! -d "$LL" ]; then cp -a /home/albus/strata166/ref/llama_b12110 "$LL"; fi
python3 /home/albus/strata166/w1031/patch_h1.py || exit 4

mkdir -p "$OUT"
cp -f /home/albus/strata166/build-v090/CMakeCache.txt "$OUT/CMakeCache.txt" 2>/dev/null
docker rm -f h1build >/dev/null 2>&1
docker run --rm --name h1build --device=/dev/kfd --device=/dev/dri \
  -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc '
set -u
cd /out
cmake -S /src -B /out -G Ninja > /out/_cmake.log 2>&1
rc=$?; echo "CMAKE_RC=$rc"; [ "$rc" -ne 0 ] && tail -8 /out/_cmake.log && exit "$rc"
ninja -j12 strata > /out/_ninja.log 2>&1
rc=$?; echo "NINJA_RC=$rc"
grep -m6 "error:" /out/_ninja.log
ls -l /out/strata 2>/dev/null; md5sum /out/strata 2>/dev/null
exit "$rc"'
