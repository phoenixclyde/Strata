#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
C=ed76b12f

echo "########## A. 提交元信息 ##########"
cd $S && git log -1 --format="%h %ad %s%n%b" --date=short $C 2>&1 | head -20

echo
echo "########## B. 改动文件与行数 ##########"
git show --stat --format="" $C 2>&1 | head -12

echo
echo "########## C. 完整 diff ##########"
git show $C 2>&1 | head -160

echo
echo "########## D. 是否受 HIP 宏门控 ##########"
git show $C 2>&1 | grep -cE "STRATA_USE_HIP|STRATA_HIP_GFX906|__HIPCC__|__HIP_PLATFORM"
