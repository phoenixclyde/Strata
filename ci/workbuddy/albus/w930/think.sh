#!/bin/bash
set -u
C="docker exec strata166-407"

echo "########## A. thinking 的判定来源 ##########"
$C sh -c "grep -n 'enable_thinking\|reasoning_effort\|def _thinking\|thinking = ' /src/serve/server.py | head -16" 2>&1

echo
echo "########## B. OpenAI 请求体解析出的采样字段（找 temperature） ##########"
$C sh -c "grep -n 'sampling = {\|sampling={\|\"temperature\": ' /src/serve/server.py | head -12" 2>&1

echo
echo "########## C. 用 enable_thinking=false 发请求，看是否注入 penalty ##########"
curl -s -m 120 http://127.0.0.1:8090/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"x","messages":[{"role":"user","content":"Say OK"}],"max_tokens":16,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}' \
  -o /tmp/it.json -w "http=%{http_code}\n" 2>&1
head -c 200 /tmp/it.json; echo
echo "--- penalty 计数（应 >0 若 instruct 生效）---"
$C sh -c "grep -cE 'penalty_last_n|penalty_present' /data/strata-huihui-ud-iq4_xs.log" 2>&1
$C sh -c "grep -E 'penalty_last_n|penalty_present' /data/strata-huihui-ud-iq4_xs.log | tail -2" 2>&1 | cut -c1-180
