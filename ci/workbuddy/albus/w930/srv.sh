#!/bin/bash
set -u
C="docker exec strata166-407"

echo "########## A. server.py:1430-1460（pf/pp 解析） ##########"
$C sh -c "sed -n '1425,1465p' /src/serve/server.py" 2>&1

echo
echo "########## B. server.py:5790-5815（max(1.5,...) 的上下文） ##########"
$C sh -c "sed -n '5788,5815p' /src/serve/server.py" 2>&1

echo
echo "########## C. server.py:7630-7650（白名单） ##########"
$C sh -c "sed -n '7630,7650p' /src/serve/server.py" 2>&1

echo
echo "########## D. 实际请求：OpenAI 路径是否注入 penalty ##########"
$C sh -c "grep -n 'def chat_completions\|def _openai\|v1/chat/completions' /src/serve/server.py | head -6" 2>&1
