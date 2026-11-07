#!/bin/bash
set -u
C="docker exec strata166-407"

echo "########## A. req_values 的构造 ##########"
$C sh -c "grep -n 'req_values' /src/serve/server.py | head -12" 2>&1

echo
echo "########## B. 5460-5490 上下文 ##########"
$C sh -c "sed -n '5455,5490p' /src/serve/server.py" 2>&1

echo
echo "########## C. OpenAI 请求体里允许的采样字段 ##########"
$C sh -c "grep -n 'penalty' /src/serve/server.py | sed -n '1,30p'" 2>&1

echo
echo "########## D. 直接从 config 开 penalty 的路径（sampling 块） ##########"
$C sh -c "grep -n 'def sampling_defaults_from_config' -A 20 /src/serve/server.py" 2>&1 | head -26
