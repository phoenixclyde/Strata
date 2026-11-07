#!/bin/sh
# 对比两个镜像里 /src/third_party/llama.cpp 的指纹
for img in "$@"; do
  echo "########## $img"
  docker run --rm --entrypoint sh "$img" -c '
    cd /src/third_party/llama.cpp 2>/dev/null || { echo NO_DIR; exit 0; }
    if [ -d .git ]; then echo HAS_GIT; else echo NO_GIT; fi
    echo "files=$(find . -type f | wc -l) bytes=$(du -sb . | cut -f1)"
    md5sum ggml/src/ggml-cuda/mmq.cuh ggml/src/ggml-cpu/iqp.cpp include/llama.h 2>/dev/null
    echo "--- BUILD-IMAGE.json"
    cat /src/BUILD-IMAGE.json 2>/dev/null
    echo
  '
done
