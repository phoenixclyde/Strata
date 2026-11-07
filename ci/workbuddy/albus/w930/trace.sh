#!/bin/bash
set -u
C="docker exec strata166-407"

echo "########## A. 刚才两次请求后，日志里有没有 penalty ##########"
$C sh -c "grep -cE 'penalty_last_n|penalty_present|penalty_freq|penalty_repeat' /data/strata-huihui-ud-iq4_xs.log" 2>&1
$C sh -c "grep -E 'penalty_last_n|penalty_present' /data/strata-huihui-ud-iq4_xs.log | tail -3" 2>&1 | cut -c1-200

echo
echo "########## B. OpenAI 请求体 -> sampling 的映射点 ##########"
$C sh -c "grep -n 'presence_penalty' /src/serve/server.py | head -20" 2>&1
echo "--- 请求 dict 里取 sampling 的地方 ---"
$C sh -c "grep -n 'sampling = ' /src/serve/server.py | head -20" 2>&1

echo
echo "########## C. keys 字符串最终写进 prompt 的位置 ##########"
$C sh -c "sed -n '13930,13950p' /src/serve/server.py" 2>&1
