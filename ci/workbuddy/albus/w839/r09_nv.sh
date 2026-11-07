#!/bin/bash
# W839-09 CUDA 侧对照：nv_defaults 是怎么被接上的
S=/home/albus/strata166/src028
echo "=== nv_defaults 的调用者 ==="
grep -rIn 'nv_defaults\|apply_nv_defaults' $S/src $S/include 2>/dev/null | grep -v 'nv_defaults.cpp:\|_test.cpp' | head -12
echo
echo "=== nv_defaults.cpp 里的入口函数签名 ==="
grep -nE '^[a-zA-Z].*\(|void |std::vector' $S/src/core/nv_defaults.cpp | head -12
echo
echo "=== 头文件声明的函数 ==="
ls $S/include/strata/core/nv_defaults.hpp 2>/dev/null && grep -nE '^[a-zA-Z].*\(' $S/include/strata/core/nv_defaults.hpp | head -10
echo
echo "=== 谁 include 了 arch_defaults.hpp（可能只是类型引用） ==="
grep -rIln 'arch_defaults.hpp' $S/src $S/include 2>/dev/null | head
echo
echo "=== gfx1151 用户是怎么拿到默认表的？搜 docs 里的说法 ==="
grep -rn 'arch default' $S/docs/*.md 2>/dev/null | head -8
