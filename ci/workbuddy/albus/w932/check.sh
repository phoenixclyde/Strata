#!/bin/bash
set -u
W=~/strata166/work/r66
B=~/strata166/gfx029-build

echo "########## A. 实验树是否存在、三补丁是否还在 ##########"
ls -d $W 2>/dev/null || echo "MISSING work/r66"
if [ -d $W ]; then
  echo "--- 三个 env 字面量（源码层）---"
  for k in STRATA_PF_GROUP_SCRATCH STRATA_PREFILL_ROUTED_STREAM STRATA_PF_HC_REGION; do
    printf "  %-30s %s\n" "$k" "$(grep -rn "$k" $W/src/prefill/prefill.cpp 2>/dev/null | wc -l)"
  done
  echo "--- prefill.cpp 大小与 mtime ---"
  ls -l $W/src/prefill/prefill.cpp 2>/dev/null | awk '{print "  ", $5, $6, $7, $8}'
fi

echo
echo "########## B. W921 编译出的二进制是否还在 ##########"
ls -l $B/strata $B/strata.bak-e0c6f250 2>/dev/null | awk '{print "  ", $9, $5}'
md5sum $B/strata 2>/dev/null
echo "--- 二进制里三个 env 字面量 ---"
for k in STRATA_PF_GROUP_SCRATCH STRATA_PREFILL_ROUTED_STREAM STRATA_PF_HC_REGION; do
  printf "  %-30s %s\n" "$k" "$(strings $B/strata 2>/dev/null | grep -c "$k")"
done

echo
echo "########## C. 单对象 .o 是否还在（决定要不要重编） ##########"
ls -l $B/CMakeFiles/strata.dir/src/prefill/prefill.cpp.o 2>/dev/null | awk '{print "  ", $5, $6, $7, $8}'

echo
echo "########## D. 当前生产二进制 ##########"
docker exec strata166-407 sh -c "md5sum /data/bin/strata-0.1.55t | cut -c1-32; ls -l /data/bin/strata-0.1.55t | awk '{print \"  size=\"\$5}'" 2>&1
