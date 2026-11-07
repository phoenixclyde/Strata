#!/bin/bash
# W839-07 入口是否被引擎调用（找出 callers）
S=/home/albus/strata166/src028
echo "=== apply_arch_defaults 的调用者 ==="
grep -rn 'apply_arch_defaults' $S/src $S/include $S/tools 2>/dev/null | head -12
echo
echo "=== arch_default_env 的调用者 ==="
grep -rn 'arch_default_env' $S/src $S/include 2>/dev/null | head -12
echo
echo "=== 分支树里的调用者（对照） ==="
grep -rn 'apply_arch_defaults' /home/albus/strata166/gfx906/src /home/albus/strata166/gfx906/include 2>/dev/null | head -12
echo
echo "=== nm 是否能读该对象 ==="
O=$S/build-028r/CMakeFiles/strata_engine.dir/src/core/arch_defaults.cpp.o
nm -C $O 2>&1 | head -5
echo "--- 用 nm -u / strings 交叉 ---"
strings -a $O 2>/dev/null | grep -E 'MI50-class|gfx_arch_is_gfx906|exact speed' | head -5
echo
echo "=== 库里有没有这个成员 ==="
ar t $S/build-028r/libstrata_engine.a 2>/dev/null | grep -c arch_defaults
ar t $S/build-028r/libstrata_core.a 2>/dev/null | grep -c arch_defaults
