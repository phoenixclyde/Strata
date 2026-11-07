#!/bin/bash
# W835: state of the llama.cpp tree and the KIntegrated tree on 166
echo "=== A. ML-gfx906/llama.cpp ==="
L=/home/albus/routeB/ML-gfx906/llama.cpp
ls -la $L | head -12
echo "--- git ---"
git -C $L log -1 --format='%h %ad %s' --date=short 2>/dev/null
git -C $L remote -v 2>/dev/null | head -2
git -C $L status --porcelain 2>/dev/null | head -20
echo "--- does it have any gfx906-specific kernel? ---"
ls $L/ggml/src/ggml-cuda/ 2>/dev/null | head -50
echo "--- grep gfx906 markers ---"
grep -rl -i "gfx906" $L/ggml/src/ggml-cuda/ 2>/dev/null | head -20
echo
echo "=== B. built binaries of llama.cpp? ==="
find $L -maxdepth 3 -name "llama-bench" -o -maxdepth 3 -name "llama-cli" -o -maxdepth 3 -name "llama-server" 2>/dev/null | head
echo
echo "=== C. KIntegrated trees ==="
for p in /home/albus/routeK/base/KIntegrated-mobydick /home/albus/routeK_gh/repo /home/albus/routeB/_clone_test/fa-integration; do
  echo "[$p]"
  git -C $p log -1 --format='  %h %ad %s' --date=short 2>/dev/null
  git -C $p remote -v 2>/dev/null | head -1
done
echo
echo "=== D. ML-gfx906 readme / notes (top) ==="
head -40 /home/albus/routeB/ML-gfx906/README.md 2>/dev/null
echo
echo "=== E. any local patch dirs for llama.cpp ==="
find /home/albus -maxdepth 3 -type d \( -name "patches" -o -name "*gfx906*patch*" \) 2>/dev/null | head -10
