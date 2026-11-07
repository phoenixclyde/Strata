#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r77

echo "=== A. ninja 自检 ==="
ninja -C $B -t commands 2>/dev/null | wc -l
echo "  （0 表示 -t commands 失效）"
ninja -C $B -t targets all 2>/dev/null | wc -l

echo
echo "=== B. 试编单个对象（可能触发 cmake 重配置，先看它说什么） ==="
docker run --rm -v $W:/src -v $B:/out -w /out strata-gfx906:0.2.9-101 \
  bash -lc "ninja CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o 2>&1 | tail -20; echo RC=\$?" 2>&1 | tail -24
