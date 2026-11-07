#!/bin/bash
# W839-13 generate.cpp 的真实宏集合
B=/home/albus/strata166/src028/build-028r
echo "=== build.ninja 里 STRATA_* 宏的总分布 ==="
grep -o -- '-DSTRATA_[A-Z0-9_]*' $B/build.ninja | sort | uniq -c | sort -rn | head -25
echo
echo "=== generate.cpp.o 这一条 build 语句的 DEFINES ==="
awk '/^build CMakeFiles\/strata.dir\/src\/program\/generate.cpp.o:/{f=1} f&&/DEFINES =/{print; exit}' $B/build.ninja | tr ' ' '\n' | grep -E '^-D' | head -30
echo
echo "=== 该 target 的 rule 与编译器 ==="
awk '/^build CMakeFiles\/strata.dir\/src\/program\/generate.cpp.o:/{f=1} f&&/^  (FLAGS|DEP_FILE|TARGET_ARCH)/{print; if(/TARGET_ARCH/){exit}}' $B/build.ninja | head -4
echo
echo "=== 全库哪些文件把 STRATA_USE_HIP 当条件用（数量） ==="
grep -rIl 'defined(STRATA_USE_HIP)' /home/albus/strata166/src028/src /home/albus/strata166/src028/include 2>/dev/null | wc -l
grep -rIl 'defined(STRATA_HIP_GFX906)' /home/albus/strata166/src028/src /home/albus/strata166/src028/include 2>/dev/null | wc -l
