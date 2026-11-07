#!/bin/bash
set -u
C="docker exec strata166-407"
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "########## A. 最近的 prefill timing 分解（后 6 条） ##########"
$C sh -c "grep -n 'strata prefill timing' $LOG | tail -6" 2>&1 | cut -c1-400

echo
echo "########## B. 这些 timing 对应的 prompt 长度 ##########"
$C sh -c "grep -E 'prompt [0-9]+ tokens' $LOG | tail -8" 2>&1 | cut -c1-200

echo
echo "########## C. 当前 KV / expert cache / VRAM 布局 ##########"
$C sh -c "grep -iE 'kv ensured|expert cache [0-9]+ slots|VRAM free|borrows [0-9]+ slots|kv_resident|KV ' $LOG | tail -8" 2>&1 | cut -c1-220

echo
echo "########## D. config 里 --kv 的位置与结构 ##########"
$C python3 -c "
import json
d=json.load(open('/data/strata-huihui-ud-iq4_xs.json'))
print('keys:', list(d.keys()))
a=d['args']
for i,x in enumerate(a):
    if x in ('--kv','--max-context','--vram-reserve-mib','--expert-cache'):
        print('  [%d] %s -> %s' % (i, x, a[i+1] if i+1<len(a) else ''))
print('args total:', len(a))
print('env keys:', sorted(d['env']))
" 2>&1

echo
echo "########## E. KV 显存公式（源码常量） ##########"
grep -n "kv_q8_bytes_per_cell" -A 8 ~/strata166/pr/strata-fork/include/strata/kernels/kv_q8.hpp 2>/dev/null | head -14
echo "---"
grep -n "kv_q4_bytes_per_cell" -A 8 ~/strata166/pr/strata-fork/include/strata/kernels/kv_q4.hpp 2>/dev/null | head -14
