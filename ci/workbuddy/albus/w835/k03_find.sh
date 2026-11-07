#!/bin/bash
# W835: find real llama.cpp source + inventory KIntegrated's gfx906-specific work
echo "=== A. hunt for real llama.cpp sources (has ggml/src) ==="
find /home/albus /opt -maxdepth 6 -type d -path "*ggml/src*" 2>/dev/null | head -20
echo "--- any dir containing ggml-cuda ---"
find /home/albus -maxdepth 8 -type d -name "ggml-cuda" 2>/dev/null | head -10
echo "--- llama.cpp tarballs / images ---"
find /home/albus -maxdepth 3 \( -name "*llama*cpp*.tar*" -o -name "*llama*.gguf" \) 2>/dev/null | head -8
docker images 2>/dev/null | grep -iE "llama|llamacpp" | head -5
echo
echo "=== B. routeK_ki028 ==="
ls -la /home/albus/routeK_ki028 2>/dev/null | head -20
git -C /home/albus/routeK_ki028 log -1 --format='%h %ad %s' --date=short 2>/dev/null
echo
echo "=== C. KIntegrated: what is gfx906-specific ==="
K=/home/albus/routeK/base/KIntegrated-mobydick
echo "--- top ---"
ls $K | head -25
echo "--- files with gfx906 in name ---"
find $K -iname "*gfx906*" -not -path "*/.git/*" 2>/dev/null | head -40
echo
echo "--- docs mentioning gfx906 ---"
find $K -maxdepth 2 -iname "*.md" 2>/dev/null | head -20
echo
echo "--- kernel files with gfx906 guards (count per file) ---"
grep -rl "gfx906" $K/csrc 2>/dev/null | head -25
