#!/bin/bash
set -u
B=~/strata166/gfx029-build
cd $B

echo "=== A. ngram.cpp.o 的完整编译命令 ==="
ninja -t commands "CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o" 2>/dev/null | tail -1 > /tmp/ng_cmd.txt
wc -c /tmp/ng_cmd.txt
head -c 500 /tmp/ng_cmd.txt
echo
echo "..."
echo "=== B. 归档命令 ==="
ninja -t commands libstrata_kernels.a 2>/dev/null | tail -1 | cut -c1-200
echo
echo "=== C. strata 链接命令（含 libstrata_kernels.a） ==="
ninja -t commands strata 2>/dev/null | grep -E "^\S*clang\+\+|/usr/bin/c\+\+|g\+\+" | tail -1 | cut -c1-300
echo
echo "=== D. strata-ci-build 容器是否存在 ==="
docker images --format "{{.Repository}}:{{.Tag}}" | grep -iE "ci-build|strata-ci" | head -3
docker ps -a --format "{{.Names}} {{.Image}}" | grep -iE "ci-build" | head -3
