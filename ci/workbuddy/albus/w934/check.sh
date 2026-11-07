#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
cd $S

echo "########## A. lookup_default.hpp 在我们树里在哪（285fa48b 的问题） ##########"
grep -n "lookup_default.hpp" src/program/generate.cpp 2>/dev/null
echo "--- 它前后 6 行（看是否在 HIP-only block 里）---"
L=$(grep -n "lookup_default.hpp" src/program/generate.cpp 2>/dev/null | head -1 | cut -d: -f1)
[ -n "${L:-}" ] && sed -n "$((L-8)),$((L+3))p" src/program/generate.cpp

echo
echo "########## B. 我们有没有 5a13c34f（PLE table lock raise soft limit） ##########"
grep -n "RLIMIT_MEMLOCK\|getrlimit\|setrlimit" src/kernels/ngram.cpp 2>/dev/null | head -8
echo "--- mlock 调用点 ---"
grep -n "mlock" src/kernels/ngram.cpp 2>/dev/null | head -5

echo
echo "########## C. e1b27d54 在 generate.cpp 的改动有多大 ##########"
git show --stat --format="" e1b27d54 -- src/program/generate.cpp 2>/dev/null
git show e1b27d54 -- src/program/generate.cpp 2>/dev/null | grep -E "^\+" | grep -vE "^\+\+\+" | head -20

echo
echo "########## D. 我们树里有没有 fatal error 自退的逻辑 ##########"
grep -c "fatal GPU error\|ERR fatal" src/program/generate.cpp 2>/dev/null
echo -n "  上游有："; git show upstream/main:src/program/generate.cpp 2>/dev/null | grep -c "ERR fatal\|fatal GPU error"

echo
echo "########## E. 引擎版本 ##########"
grep -m1 "project(strata VERSION" CMakeLists.txt
echo -n "  上游："; git show upstream/main:CMakeLists.txt 2>/dev/null | grep -m1 "project(strata VERSION"
