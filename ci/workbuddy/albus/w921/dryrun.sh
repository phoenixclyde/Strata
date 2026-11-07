#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r66
LL=~/routeB/ML-gfx906/llama.cpp

echo "=== 备份 build 关键文件 ==="
cp -a $B/build.ninja $B/CMakeCache.txt /tmp/ 2>/dev/null && echo "backed up to /tmp/"
du -sh $B 2>/dev/null

echo
echo "=== 试跑 dry-run：bind llama.cpp 后要编多少 ==="
docker run --rm -v $W:/src -v $B:/out -v $LL:/llama.cpp -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
    ninja -n strata 2>&1 | tail -5
    echo "--- 编译单元数 ---"
    ninja -n strata 2>&1 | grep -cE "^\[[0-9]+/[0-9]+\] (Building|Linking)"
  '
