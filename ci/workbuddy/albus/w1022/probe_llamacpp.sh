#!/bin/sh
# 在容器内查 llama.cpp 的版本标识（只读）
cd /src/third_party/llama.cpp || exit 3
echo "=== .git ?"
if [ -d .git ]; then echo HAS_GIT; else echo NO_GIT; fi
echo "=== llama.h 版本宏"
grep -n "LLAMA_BUILD_NUMBER\|LLAMA_COMMIT" include/llama.h 2>/dev/null | head -4
echo "=== CMakeLists 里的 build number 定义"
grep -n "LLAMA_BUILD_NUMBER\|LLAMA_COMMIT\|project(llama" CMakeLists.txt 2>/dev/null | head -6
echo "=== ggml 头里的版本"
grep -n "GGML_VERSION\|GGML_COMMIT" ggml/include/ggml.h 2>/dev/null | head -4
echo "=== iqp.cpp（v0.2.11 才需要）"
ls -l ggml/src/ggml-cpu/iqp.cpp 2>/dev/null || echo NO_IQP
echo "=== 关键文件 md5"
md5sum ggml/src/ggml-cuda/mmq.cuh ggml/src/ggml-cpu/iqp.cpp include/llama.h 2>/dev/null
echo "=== 目录指纹（文件数 + 总字节）"
find . -type f | wc -l
du -sb . 2>/dev/null | cut -f1
echo "=== VERSION / 顶层说明"
ls | head -12
