#!/bin/bash
# b12169 download, with integrity checks: last attempt left a 23 MB truncated tarball
# and `tar xzf` failed silently inside a piped script.
set -uo pipefail
REF=/home/albus/strata166/ref
TAR=$REF/llama-b12169.tar.gz
DST=$REF/llama_b12169
SHA=3ed7284f2d9e22b2d1a7d05c1416c00c5a9f0bc7

rm -rf "$DST" "$TAR"
echo "downloading $SHA"
curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 300 \
     -o "$TAR" "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/$SHA"
echo "curl rc=$?"
ls -l "$TAR" || exit 3

N=$(tar tzf "$TAR" 2>/dev/null | wc -l)
echo "tar entries=$N"
[ "$N" -gt 3000 ] || { echo TAR_INCOMPLETE; exit 4; }

mkdir -p "$DST"
tar xzf "$TAR" -C "$DST" --strip-components=1
echo "tar rc=$?"
echo "files=$(find "$DST" -type f | wc -l) bytes=$(du -sb "$DST" | cut -f1)"
ls "$DST/ggml/src/ggml-cpu/iqp.cpp" 2>/dev/null || echo "iqp: ABSENT (expected)"
head -1 "$DST/ggml/src/ggml-cuda/mmq.cuh"
