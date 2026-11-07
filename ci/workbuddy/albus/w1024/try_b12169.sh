#!/bin/bash
# Try the NEWEST llama.cpp tag (b12169) with the port already kept on exp/lcpp-b12129.
# Same discipline as W1023: separate build dir, clean objects, mainline untouched afterwards.
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
REF=/home/albus/strata166/ref
NEW=/home/albus/strata166/build-lcpp
SHA=3ed7284f2d9e22b2d1a7d05c1416c00c5a9f0bc7

if [ ! -d "$REF/llama_b12169" ]; then
  curl -sSL -o "$REF/llama-b12169.tar.gz" "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/$SHA" || { echo DOWNLOAD_FAIL; exit 3; }
  mkdir -p "$REF/llama_b12169"
  tar xzf "$REF/llama-b12169.tar.gz" -C "$REF/llama_b12169" --strip-components=1 || { echo UNTAR_FAIL; exit 4; }
fi
echo "tree files=$(find "$REF/llama_b12169" -type f | wc -l) bytes=$(du -sb "$REF/llama_b12169" | cut -f1)"
echo "iqp: $(ls "$REF/llama_b12169/ggml/src/ggml-cpu/iqp.cpp" 2>/dev/null || echo ABSENT)"

cd "$R" || exit 3
git checkout -q exp/lcpp-b12129 || { echo CHECKOUT_FAIL; exit 5; }
echo "on branch: $(git rev-parse --abbrev-ref HEAD) $(git rev-parse --short HEAD)"

docker run --rm --security-opt label=disable \
  -v "$R":/src -v "$NEW":/out -v "$REF/llama_b12169":/llama.cpp \
  strata-gfx906:0.2.11-101 bash -lc '
cd /out
find . -name "*.o" -delete 2>/dev/null
find . -name "*.a" -delete 2>/dev/null
rm -f strata
cmake -DSTRATA_GGML_DIR=/llama.cpp . > /tmp/cm3.log 2>&1
echo "cmake rc=$?"; tail -3 /tmp/cm3.log
ninja -j6 strata > /tmp/nj3.log 2>&1
echo "ninja rc=$?"
echo "errors=$(grep -c "error:" /tmp/nj3.log)"
grep "error:" /tmp/nj3.log | head -10
ls -l strata 2>/dev/null; md5sum strata 2>/dev/null
./strata --version 2>/dev/null
'

cd "$R" && git checkout -q gfx906/mi50
echo "back on: $(git rev-parse --abbrev-ref HEAD) $(git rev-parse --short HEAD) dirty=$(git status --porcelain | wc -l)"
