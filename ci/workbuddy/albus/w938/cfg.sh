#!/bin/bash
set -u
T=/home/albus/strata166/transfer/llama.cpp-3cf0325.tar.gz
D=/home/albus/strata166/llama.cpp
R=/home/albus/strata166/work/rebase-trial
B=/home/albus/strata166/build-r28

echo "=== 1) 解 llama.cpp 到 $D ==="
rm -rf "$D"; mkdir -p "$D"
tar xzf "$T" -C "$D" 2>&1 | head -3
# flatten if the archive has a single top dir
inner=$(find "$D" -maxdepth 1 -mindepth 1 -type d | head -1)
if [ -n "$inner" ] && [ ! -f "$D/ggml/CMakeLists.txt" ]; then
  echo "flattening $inner"
  shopt -s dotglob
  mv "$inner"/* "$D"/ 2>/dev/null
  rmdir "$inner"
  shopt -u dotglob
fi
ls -d "$D/ggml" "$D/gguf-py" 2>/dev/null
[ -f "$D/ggml/CMakeLists.txt" ] && echo "ggml OK" || echo "GGML MISSING"

echo
echo "=== 2) 配置 build-r28 ==="
rm -rf "$B"; mkdir -p "$B"
docker run --rm -v "$R":/src -v "$B":/out -v "$D":/llama.cpp:ro -w /out strata-gfx906:0.2.9-101 bash -lc '
cmake -G Ninja -S /src -B /out \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DSTRATA_ENABLE_CUDA=ON -DSTRATA_ENABLE_HIP=OFF -DSTRATA_HIP_GFX906=ON \
  -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_PREFILL_MMQ=ON \
  -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_DSV41=OFF -DSTRATA_BUILD_CONVERSATION_TESTS=OFF \
  -DSTRATA_GGML_DIR=/llama.cpp > /out/_cmake.log 2>&1
echo "CMAKE_RC=$?"
tail -6 /out/_cmake.log
echo "--- 关键选项 ---"
grep -E "^(STRATA_(ENABLE_CUDA|HIP_GFX906|PREFILL_MMQ|MMQ_KQUANTS|NATIVE_EXPERTS|GGML_DIR)|CMAKE_BUILD_TYPE):" /out/CMakeCache.txt
' 2>&1 | tail -22
