#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
C="docker exec strata166-407"

echo "########## A. OpenAI API 的 presence_penalty 解析 ##########"
grep -rn "presence_penalty\|frequency_penalty\|repetition_penalty" --include=*.cpp --include=*.py --include=*.hpp $S/src $S/include 2>/dev/null | head -14

echo
echo "########## B. 模型卡默认（presence 1.5 那段） ##########"
grep -rn "presence_penalty 1.5\|presence = 1.5\|presence_penalty\s*=\s*1.5" --include=*.cpp --include=*.hpp --include=*.json $S/src $S/include 2>/dev/null | head -8
grep -rn "model card\|model_card" --include=*.cpp $S/src/program/generate.cpp 2>/dev/null | head -6

echo
echo "########## C. 默认 sampling 结构体 ##########"
grep -rn "struct SamplerParams" -A 22 $S/include/strata/kernels/sampler.hpp 2>/dev/null | head -28

echo
echo "########## D. 服务端默认值（server 端） ##########"
$C sh -c "grep -rn 'presence_penalty\|frequency_penalty' /src/serve/*.py /src/serve/**/*.py 2>/dev/null | head -10" 2>&1
