#!/bin/sh
# 整棵树的确定性指纹：路径排序 + 每文件 md5 -> 再 md5
# 用于证明「镜像里的 llama.cpp」与「引擎编译时挂载的 llama.cpp」是同一份
tree_hash() {
  cd "$1" || return 3
  find . -type f -print0 | LC_ALL=C sort -z | xargs -0 md5sum 2>/dev/null | md5sum | cut -d' ' -f1
}

echo "mirror  /src/third_party/llama.cpp : $(docker exec strata166-407 sh -c 'cd /src/third_party/llama.cpp && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 md5sum 2>/dev/null | md5sum | cut -d" " -f1')"
echo "bake    ref/llama_3cf0325          : $(tree_hash /home/albus/strata166/ref/llama_3cf0325)"
echo "image   0.2.11-101 /src/third_party : $(docker run --rm --entrypoint sh strata-gfx906:0.2.11-101 -c 'cd /src/third_party/llama.cpp && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 md5sum 2>/dev/null | md5sum | cut -d" " -f1')"
echo "=== 二进制里能否找到 llama.cpp 的 build 号"
docker exec strata166-407 sh -c 'strings -a /data/bin/strata-0.1.57-001 2>/dev/null | grep -E "^b[0-9]{4,5}$|3cf0325|llama.cpp" | sort -u | head -8'
