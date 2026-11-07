#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
cd $S

echo "########## A. 5a13c34f 完整提交信息 ##########"
git log -1 --format="%h %ad %s%n%n%b" --date=short 5a13c34f 2>/dev/null | head -22

echo
echo "########## B. 改动文件与 diff ##########"
git show --stat --format="" 5a13c34f 2>/dev/null
echo "--- 正文 ---"
git show 5a13c34f 2>/dev/null | sed -n '/^diff/,$p' | head -90

echo
echo "########## C. 我们树里 ngram.cpp 对应位置（与上游的差异） ##########"
grep -n "mlock\|RLIMIT_MEMLOCK\|getrlimit\|setrlimit" src/kernels/ngram.cpp 2>/dev/null | head -10
echo "--- 我方 440-470 行 ---"
sed -n '435,470p' src/kernels/ngram.cpp

echo
echo "########## D. hard limit 实际值（三层） ##########"
echo "--- 容器内 ---"
docker exec strata166-407 sh -c "ulimit -Sl; ulimit -Hl; grep -i 'max locked' /proc/1/limits"
echo "--- 宿主 dockerd ---"
systemctl show docker --property=LimitMEMLOCK 2>/dev/null
echo "--- 宿主 shell ---"
ulimit -Sl; ulimit -Hl
