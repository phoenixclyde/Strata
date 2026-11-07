#!/bin/bash
set -u
C="docker exec strata166-407"
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "########## A. 我们真实 prompt 的长度分布（>8192 的占比） ##########"
$C sh -c "grep -oE 'prompt [0-9]+ tokens' $LOG | awk '{print \$2}' | sort -n | awk '
{a[NR]=\$1}
END{
  n=NR;
  printf \"  样本 %d 个\n\", n;
  split(\"0 1024 2048 4096 8192 16384 32768 131072 999999\", b, \" \");
  for (i=1;i<=9;i++) {
    lo=b[i]; hi=b[i+1]; c=0;
    for (j=1;j<=n;j++) if (a[j]>lo && a[j]<=hi) c++;
    if (c>0) printf \"  (%6d, %7d]  %6d  %5.1f%%\n\", lo, (hi==999999?0:hi), c, 100*c/n;
  }
}'" 2>&1

echo
echo "########## B. 中位数 / 最大值 ##########"
$C sh -c "grep -oE 'prompt [0-9]+ tokens' $LOG | awk '{print \$2}' | sort -n | awk '{a[NR]=\$1} END{printf \"  min=%d  median=%d  p90=%d  max=%d\n\", a[1], a[int(NR*0.5)], a[int(NR*0.9)], a[NR]}'" 2>&1

echo
echo "########## C. CPU share 在 HIP 上是否生效（日志） ##########"
$C sh -c "grep -inE 'cpu share|CPU share|share is ON|share off|arm_cpu_share' $LOG | tail -6" 2>&1 | cut -c1-190

echo
echo "########## D. CPU share 的 arm 条件（源码） ##########"
S=~/strata166/pr/strata-fork
grep -n "arm_cpu_share" $S/src/prefill/prefill.cpp $S/src/program/generate.cpp 2>/dev/null | head -8
grep -n "HIP stay off\|STRATA_HIP_GFX906\|g_share_default =" $S/src/prefill/prefill.cpp 2>/dev/null | head -8
