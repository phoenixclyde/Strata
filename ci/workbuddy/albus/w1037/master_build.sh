#!/bin/bash
# W1037: can we go to master?  Build "llama.cpp master (bcb01528) + mmq* @4c1004c" and see what it costs.
set -u
R=/home/albus/strata166/tmp/w1037
M=$R/llama-master
SHA=bcb0152876e8f0b684ba70d3defcab6cdf35adb5
TAR=$R/llama-master.tar.gz
IMG=strata-gfx906:0.2.11-101
B=/home/albus/strata166/build-masterp

df -h /home/albus | tail -1

if [ ! -f "$TAR" ]; then
  curl -sL -m 300 "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/$SHA" -o "$TAR" || { echo "FAIL download"; exit 1; }
fi
ls -l "$TAR"

if [ ! -d "$M" ]; then
  mkdir -p "$R/xm" && rm -rf "$R/xm"/*
  tar -xzf "$TAR" -C "$R/xm" || { echo "FAIL untar"; exit 1; }
  mv "$R/xm"/llama.cpp-* "$M" || { echo "FAIL move"; exit 1; }
fi
echo "master files: $(find "$M" -type f | wc -l)"

# pin the MMQ family back to 2026-10-19 (the same K10 point that measured free)
OLD=$(ls -d "$R"/x/llama.cpp-4c1004c*/ggml/src/ggml-cuda | head -1)
echo "mmq source: $OLD"
cp -f "$OLD"/mmq.cu "$OLD"/mmq.cuh "$OLD"/mmq-load-tiles.cuh "$OLD"/mmq-vec-dot.cuh "$M/ggml/src/ggml-cuda/" || exit 1
cp -f "$OLD"/mmq-config-*.cuh "$M/ggml/src/ggml-cuda/" || exit 1
md5sum "$M/ggml/src/ggml-cuda/mmq.cuh" | cut -c1-12

if [ ! -d "$B" ]; then
  cp -a /home/albus/strata166/build-k10p "$B" || { echo "FAIL copy build dir"; exit 1; }
fi

docker run --rm -v /home/albus/strata166/pr/k10:/src -v "$B":/out -v "$M":/llama.cpp -w /out "$IMG" \
  sh -c "cmake -S /src -B /out -DSTRATA_MMQ_TQ_OVERLAY=ON > /tmp/c.log 2>&1; echo CFG=\$?; grep -i trellis /tmp/c.log; \
         ninja -j 12 > /tmp/b.log 2>&1; echo BLD=\$?; grep -c '^FAILED' /tmp/b.log; grep -m8 'error:' /tmp/b.log; md5sum /out/strata"
