#!/bin/bash
set -u
SRC=~/strata166/pr/strata-fork
W=~/strata166/work/r66
cd $W || exit 1

echo "=== 1. 从原版恢复 generate.cpp ==="
cp $SRC/src/program/generate.cpp src/program/generate.cpp
md5sum src/program/generate.cpp $SRC/src/program/generate.cpp

echo
echo "=== 2. 只应用 generate.cpp 的补丁（git apply 支持路径过滤）==="
git apply --include=src/program/generate.cpp /tmp/r68.patch 2>&1 && echo "applied"
grep -c "STRATA_SERVE_STOP_BOUND" src/program/generate.cpp

echo
echo "=== 3. 只改补丁的 4 处 #if（按上下文精确匹配）==="
python3 - <<'PY'
import io
p = "src/program/generate.cpp"
s = io.open(p, encoding="utf-8").read()
NEW = "#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)"
cases = [
 ('#if defined(STRATA_USE_HIP)\n#include "strata/core/serve_stop_bound.hpp"', 1, "include"),
 ('#if defined(STRATA_USE_HIP)\n            // on by default (HIP, where it was measured', 1, "stop_bound 变量"),
 ('#if defined(STRATA_USE_HIP)\n                    if (stop_bound)\n                        a = strata::core::serve_stop_bound(a + 1,', 1, "应用点 1"),
 ('#if defined(STRATA_USE_HIP)\n                // A merged window contains prompt rows', 1, "应用点 2"),
]
for old, n, name in cases:
    cnt = s.count(old)
    assert cnt == n, (name, cnt)
    s = s.replace(old, old.replace("#if defined(STRATA_USE_HIP)", NEW, 1), 1)
    print("  patched:", name)
io.open(p, "w", encoding="utf-8").write(s)
PY

echo
echo "=== 4. 核对：只有 4 处是复合条件，原有 3 处保持原样 ==="
grep -nE "^#if defined\(STRATA_USE_HIP\)" src/program/generate.cpp | head -40
