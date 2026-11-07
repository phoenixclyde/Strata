#!/bin/bash
B=~/strata166/gfx029-build
echo "=== 构建目录指向的源码树 ==="
grep -E "^CMAKE_HOME_DIRECTORY|^CMAKE_BUILD_TYPE|^CMAKE_CXX_COMPILER:" $B/CMakeCache.txt 2>/dev/null

echo
echo "=== 产物 ==="
ls -l $B/strata 2>/dev/null; md5sum $B/strata 2>/dev/null
echo "生产运行件 md5: a97f4479eb17113d741c5362a5777b48"

echo
echo "=== prefill.cpp 的编译规则 ==="
grep -n "prefill.cpp.o:" -A6 $B/build.ninja | head -20

echo
echo "=== 链接规则（引擎）==="
grep -n "^build strata:" -A4 $B/build.ninja | head -12
