#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
C="docker exec strata166-407"

echo "########## A. 我们树里有没有这个补丁 ##########"
for k in penalty_counts_prompt penalty_window_from STRATA_PENALTY_PROMPT penalty_rows; do
  printf "%-26s %s\n" "$k" "$(grep -rn "$k" --include=*.hpp --include=*.cpp --include=*.cu $S/include $S/src 2>/dev/null | wc -l)"
done

echo
echo "########## B. 生产 config 的 sampling 块 ##########"
$C python3 -c "
import json
d=json.load(open('/data/strata-huihui-ud-iq4_xs.json'))
print('keys:', list(d.keys()))
print('sampling:', json.dumps(d.get('sampling'), ensure_ascii=False))
print('model_name:', d.get('model_name'))
print('backend:', d.get('backend'))
" 2>&1

echo
echo "########## C. 引擎启动时的采样默认（日志） ##########"
$C sh -c "grep -inE 'presence|frequency|repetition|penalty|sampling' /data/strata-huihui-ud-iq4_xs.log | tail -8" 2>&1 | cut -c1-190

echo
echo "########## D. 服务端默认采样值（源码） ##########"
grep -rn "presence_penalty\|penalty_last_n\|repetition_penalty" --include=*.hpp --include=*.cpp $S/src/program/generate.cpp 2>/dev/null | head -12
