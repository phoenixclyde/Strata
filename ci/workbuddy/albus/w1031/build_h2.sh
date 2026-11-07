#!/bin/bash
# H2: 0.9.0 的 ggml-base/ggml-cpu + **pin 的 ggml-cuda（MMQ 全家）**，配未改过的生产粘合层（pin API）。
# 若 prefill 回到 ~532 ⇒ 3.8% 在 MMQ kernel 重写（mmq.cuh +566 行）里；若仍 ~513 ⇒ 在 ggml-cpu/主机侧。
set -u
IMG=strata-gfx906:0.2.11-101
SRC=/home/albus/strata166/pr/strata-fork          # 原样：pin 的 API 期望
PIN=/home/albus/strata166/ref/llama_3cf0325/ggml/src/ggml-cuda
LL=/home/albus/strata166/w1031/llama_h2
OUT=/home/albus/strata166/build-h2

if [ ! -d "$LL" ]; then cp -a /home/albus/strata166/ref/llama_b12110 "$LL"; fi
for f in mmq.cuh mmq-load-tiles.cuh mmq-vec-dot.cuh vecdotq.cuh quantize.cu quantize.cuh mma.cuh dequantize.cuh; do
  cp -f "$PIN/$f" "$LL/ggml/src/ggml-cuda/$f" || exit 5
done
echo "--- headers now:"; md5sum "$LL/ggml/src/ggml-cuda/mmq.cuh" "$PIN/mmq.cuh"

mkdir -p "$OUT"; cp -f /home/albus/strata166/build-v090/CMakeCache.txt "$OUT/CMakeCache.txt" 2>/dev/null
docker rm -f h2build >/dev/null 2>&1
docker run --rm --name h2build --device=/dev/kfd --device=/dev/dri \
  -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc '
set -u
cd /out
cmake -S /src -B /out -G Ninja > /out/_cmake.log 2>&1
rc=$?; echo "CMAKE_RC=$rc"; [ "$rc" -ne 0 ] && tail -10 /out/_cmake.log && exit "$rc"
ninja -j12 strata > /out/_ninja.log 2>&1
rc=$?; echo "NINJA_RC=$rc"
grep -m6 "error:" /out/_ninja.log
ls -l /out/strata 2>/dev/null; md5sum /out/strata 2>/dev/null
exit "$rc"'
