#!/bin/bash
B=~/strata166/gfx029-build
echo "=== CMakeCache 里的 ggml / llama 路径 ==="
grep -iE "GGML_DIR|llama|STRATA_GGML" $B/CMakeCache.txt | head -10

echo
echo "=== 镜像内有 /llama.cpp 吗 ==="
docker run --rm --entrypoint sh strata-gfx906:0.2.9-101 -c 'ls -d /llama.cpp /llama.cpp/ggml 2>&1; ls /llama.cpp 2>/dev/null | head -5'

echo
echo "=== 宿主有 llama.cpp 吗 ==="
ls -d ~/routeB/ML-gfx906/llama.cpp 2>/dev/null && (cd ~/routeB/ML-gfx906/llama.cpp && git log -1 --format='%h %ad' --date=short 2>/dev/null)
ls -d ~/strata166/pr/strata-fork/third_party/ggml 2>/dev/null && cat ~/strata166/pr/strata-fork/third_party/ggml/VERSION.txt 2>/dev/null

echo
echo "=== CMakeLists 里 ggml 的解析 ==="
sed -n '1910,1930p' ~/strata166/pr/strata-fork/CMakeLists.txt
