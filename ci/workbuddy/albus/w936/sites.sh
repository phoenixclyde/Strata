#!/bin/bash
set -u
W=~/strata166/work/r77
cd "$W" || exit 1
echo "=== 调用点 1: ver.run(...) 附近 ==="
grep -n "ver.run(T, window.data()" src/program/generate.cpp | head -2
L=$(grep -n "ver.run(T, window.data()" src/program/generate.cpp | head -1 | cut -d: -f1)
[ -n "$L" ] && sed -n "$((L-4)),$((L+4))p" src/program/generate.cpp

echo
echo "=== 调用点 2: ver.commit(a + 1, err) ==="
grep -n "!ver.commit(a + 1, err)" src/program/generate.cpp | head -2
L=$(grep -n "!ver.commit(a + 1, err)" src/program/generate.cpp | head -1 | cut -d: -f1)
[ -n "$L" ] && sed -n "$((L-1)),$((L+4))p" src/program/generate.cpp

echo
echo "=== 调用点 3: ver.wait_commit(err) ==="
grep -n "!ver.wait_commit(err)" src/program/generate.cpp | head -2
L=$(grep -n "!ver.wait_commit(err)" src/program/generate.cpp | head -1 | cut -d: -f1)
[ -n "$L" ] && sed -n "$((L-2)),$((L+4))p" src/program/generate.cpp

echo
echo "=== 头文件 ==="
head -40 src/program/generate.cpp | grep -nE "#include <(cstdio|cstdlib|string|cmath)>"
echo "--- cuda_runtime 是否可见 ---"
grep -n "cuda_runtime" src/program/generate.cpp | head -3
