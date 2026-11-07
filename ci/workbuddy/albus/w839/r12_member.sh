#!/bin/bash
# W839-12 链接丢成员的真因
B=/home/albus/strata166/src028/build-028r
G=$B/CMakeFiles/strata.dir/src/program/generate.cpp.o
O=$B/CMakeFiles/strata_engine.dir/src/core/arch_defaults.cpp.o
echo "=== generate.cpp.o 是否引用 apply_arch_defaults ==="
nm -C $G 2>/dev/null | grep -c 'apply_arch_defaults'
nm -C $G 2>/dev/null | grep 'apply_arch_defaults' | head -3
echo "=== generate.cpp.o 时间戳 ==="
ls -la $G | cut -c1-90
echo
echo "=== arch_defaults.cpp.o 导出的符号（前 20） ==="
nm -C --defined-only $O 2>/dev/null | head -20
echo
echo "=== 归档里该成员是否真的是新版本 ==="
cd /tmp && rm -rf arx && mkdir arx && cd arx
ar x /home/albus/strata166/src028/build-028r/libstrata_engine.a arch_defaults.cpp.o 2>/dev/null
ls -la arch_defaults.cpp.o 2>/dev/null | cut -c1-80
grep -a -c -F 'MI50-class' arch_defaults.cpp.o 2>/dev/null
echo
echo "=== 二进制里 strings 交叉 ==="
strings -a $B/strata | grep -c 'MI50-class'
strings -a $B/strata | grep -c 'exact speed switches'
echo "=== 该二进制是否真为 HIP 构型 ==="
strings -a $B/strata | grep -c 'STRATA_USE_HIP' 
grep -o 'STRATA_USE_HIP' $B/build.ninja | head -1
grep -c 'DSTRATA_USE_HIP' $B/build.ninja
