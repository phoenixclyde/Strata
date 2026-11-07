#!/bin/bash
S=/home/albus/strata166
echo "=== A. 可能的 llama 树 ==="
ls -d $S/tmp/w1037/llama-* $S/ref/llama_* 2>/dev/null
echo
echo "=== B. b12180 那次构建用的树（CMakeCache）==="
for b in build-masterp build-k10p; do
  echo "--- $b"
  grep -m3 -E "CMAKE_HOME_DIRECTORY|LLAMA|CMAKE_CACHEFILE_DIR" $S/$b/CMakeCache.txt 2>/dev/null | head -5
  grep -o "/llama.cpp" $S/$b/build.ninja 2>/dev/null | head -1
done
echo
echo "=== C. 各 llama 树的身份 ==="
for d in $S/tmp/w1037/llama-master $S/tmp/w1037/llama-k10; do
  [ -d "$d" ] || continue
  echo "--- $d"
  grep -m1 "LLAMA_BUILD_NUMBER\|LLAMA_COMMIT" $d/CMakeLists.txt 2>/dev/null
  ls $d/ggml/src/ggml-cuda/mmq-config-gcn.cuh 2>/dev/null && md5sum $d/ggml/src/ggml-cuda/mmq.cuh | cut -c1-12
done
echo
echo "=== D. port-all 工作树状态 ==="
cd $S/pr/port-all && git log --oneline -2 && git status --porcelain | head -6 && echo "dirty=$(git status --porcelain | wc -l)"
echo
echo "=== E. 构建目录与磁盘 ==="
ls -d $S/build-* 2>/dev/null
df -h $S | tail -1
echo
echo "=== F. 现有 pa* 件 ==="
ls -l $S/data/bin/strata-0.1.57-pa* 2>/dev/null
