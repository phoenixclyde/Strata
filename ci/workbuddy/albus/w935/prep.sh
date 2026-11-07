#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
W=~/strata166/work/r77

echo "########## A. 建实验树（rsync 保留 mtime，避免全量重编） ##########"
rm -rf $W
time rsync -a --exclude=.git $S/ $W/ 2>&1 | tail -3
echo "  大小: $(du -sh $W | cut -f1)"

echo
echo "########## B. 打 5a13c34f 到 ngram.cpp ##########"
cd $W
git -C $S show 5a13c34f -- src/kernels/ngram.cpp > /tmp/ple.patch 2>/dev/null
wc -l /tmp/ple.patch
# 实验树没有 .git，用 patch 命令
patch -p1 --dry-run < /tmp/ple.patch 2>&1 | tail -5
echo "--- 实打 ---"
patch -p1 < /tmp/ple.patch 2>&1 | tail -5

echo
echo "########## C. 确认补丁生效 ##########"
grep -c "getrlimit\|setrlimit\|RLIMIT_MEMLOCK" src/kernels/ngram.cpp
grep -n "raised to\|this program may lock only" src/kernels/ngram.cpp | head -4

echo
echo "########## D. ngram.cpp 的编译命令与归档位置 ##########"
cd ~/strata166/gfx029-build
ninja -t commands strata 2>/dev/null | grep -E "ngram\.cpp\.o" | head -2 > /tmp/ngram_cmd.txt
wc -l /tmp/ngram_cmd.txt
head -c 400 /tmp/ngram_cmd.txt
echo
echo "--- ngram.cpp.o 属于哪个库 ---"
ninja -t commands strata 2>/dev/null | grep "ngram.cpp.o" | grep -oE "lib[a-z_]+\.a" | sort -u
echo "--- 产物路径 ---"
find . -name "ngram.cpp.o" 2>/dev/null | head -3
