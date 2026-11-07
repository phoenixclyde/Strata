#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r66
LL=~/routeB/ML-gfx906/llama.cpp

echo "=== 用 ninja -t commands 抽 prefill.cpp.o 的编译命令（不触发 cmake）==="
docker run --rm -v $W:/src -v $B:/out -v $LL:/llama.cpp -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
    ninja -t commands CMakeFiles/strata_prefill.dir/src/prefill/prefill.cpp.o 2>&1 | tail -3
    echo "=== 链接命令（最后一行）==="
    ninja -t commands strata 2>&1 | tail -1 | cut -c1-300
  '
