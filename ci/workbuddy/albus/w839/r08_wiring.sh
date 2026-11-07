#!/bin/bash
# W839-08 全库（含 python/工具）查 arch_default 的接线点
S=/home/albus/strata166/src028
echo "=== 全库（不限后缀） ==="
grep -rIn 'arch_default' $S --include='*' 2>/dev/null | grep -v '/build-028' | grep -v '_test.cpp' | head -25
echo
echo "=== python 侧是否设置这些 env ==="
grep -rIn 'GFX906\|GDN_HEAD\|STRATA_SELECT_SIMT\|arch_default' $S/serve/*.py 2>/dev/null | head -15
echo
echo "=== 引擎启动处 env 的设置（generate.cpp main）==="
grep -n 'setenv' $S/src/program/generate.cpp | head -20
echo
echo "=== 是否有个 central env 初始化文件 ==="
grep -rIln 'setenv(' $S/src | head -12
