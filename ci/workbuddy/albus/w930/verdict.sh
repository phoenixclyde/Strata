#!/bin/bash
set -u
C="docker exec strata166-407"

echo "########## A. MODEL_CARD_SAMPLING 完整定义 ##########"
$C sh -c "sed -n '8825,8846p' /src/serve/server.py" 2>&1

echo
echo "########## B. svc.shared / sampling_defaults 的来源 ##########"
$C sh -c "grep -n 'self.shared\s*=\|sampling_defaults\s*=' /src/serve/server.py | head -8" 2>&1

echo
echo "########## C. model_arch 的实际取值 ##########"
$C sh -c "grep -n 'self.model_arch\s*=\|model_arch =' /src/serve/server.py | head -6" 2>&1

echo
echo "########## D. 实测：发一个请求，看引擎是否收到 penalty ##########"
curl -s -m 120 http://127.0.0.1:8090/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"x","messages":[{"role":"user","content":"Reply with exactly: PENALTY_PROBE_OK"}],"max_tokens":16,"temperature":0}' \
  -o /tmp/pp.json -w "http=%{http_code}\n" 2>&1
head -c 300 /tmp/pp.json 2>/dev/null
echo
echo "--- 服务端最近日志（看 prompt 里有没有 penalty key）---"
$C sh -c "grep -E 'penalty_last_n|penalty_present|penalty_freq|penalty_repeat' /data/strata-huihui-ud-iq4_xs.log | tail -3" 2>&1 | cut -c1-160
