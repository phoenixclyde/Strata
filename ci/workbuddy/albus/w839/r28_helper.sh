#!/bin/bash
# W839-28 读 gfx_arch_is
H=/home/albus/strata166/src028/include/strata/kernels/gfx_arch.hpp
sed -n '1,40p' $H
echo "=== 谁在引擎里调用 apply_arch_defaults（构建树）==="
grep -n "apply_arch_defaults" /home/albus/strata166/src028/src/program/generate.cpp
echo "=== 该行上下文 ==="
N=$(grep -n "apply_arch_defaults" /home/albus/strata166/src028/src/program/generate.cpp | head -1 | cut -d: -f1)
sed -n "$((N-6)),$((N+4))p" /home/albus/strata166/src028/src/program/generate.cpp
