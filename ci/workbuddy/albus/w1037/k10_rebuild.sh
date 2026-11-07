#!/bin/bash
# W1037: reconstruct K10 from upstream (no reliance on the lost 2026-11-07 tree).
#   llama-k10 = llama.cpp b12110 tree  +  ggml/src/ggml-cuda/mmq*  from llama.cpp 4c1004c (2026-10-19)
set -u
R=/home/albus/strata166/tmp/w1037
K=$R/llama-k10
SHA=4c1004c49221b07c3b8108977e3d1991fc9f45cc
TAR=$R/llama-4c1004c.tar.gz

df -h /home/albus | tail -1

if [ ! -f "$TAR" ]; then
  curl -sL -m 300 "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/$SHA" -o "$TAR" || { echo "FAIL download"; exit 1; }
fi
ls -l "$TAR"

rm -rf "$K"
cp -a /home/albus/strata166/ref/llama_b12110 "$K" || { echo "FAIL copy b12110"; exit 1; }
echo "b12110 files: $(find "$K" -type f | wc -l)"

mkdir -p "$R/x" && rm -rf "$R/x"/* 
tar -xzf "$TAR" -C "$R/x" --wildcards '*/ggml/src/ggml-cuda/mmq*' || { echo "FAIL untar"; exit 1; }
NEW=$(ls -d "$R/x"/*/ggml/src/ggml-cuda | head -1)
echo "patched-from: $NEW"
ls "$NEW"/mmq* | head -20

md5sum "$K/ggml/src/ggml-cuda/mmq.cuh" | cut -c1-12
cp -f "$NEW"/mmq.cu "$NEW"/mmq.cuh "$NEW"/mmq-load-tiles.cuh "$NEW"/mmq-vec-dot.cuh "$K/ggml/src/ggml-cuda/" 2>/dev/null
cp -f "$NEW"/mmq-config-*.cuh "$K/ggml/src/ggml-cuda/" 2>/dev/null
echo "after overlay:"
md5sum "$K/ggml/src/ggml-cuda/mmq.cuh" | cut -c1-12
for f in mmq.cu mmq.cuh mmq-load-tiles.cuh mmq-vec-dot.cuh; do echo "  $f $(md5sum "$K/ggml/src/ggml-cuda/$f" | cut -c1-12)"; done
ls "$K/ggml/src/ggml-cuda/" | grep -c '^mmq-config'
