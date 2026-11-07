#!/bin/bash
set -u
C="docker exec strata166-407"

echo "########## A. model_card_sampling 定义 ##########"
$C sh -c "grep -n 'def model_card_sampling' -A 40 /src/serve/server.py" 2>&1 | head -50

echo
echo "########## B. qwen 系列的 presence_penalty 默认 ##########"
$C sh -c "grep -n 'presence_penalty' /src/serve/server.py | head -20" 2>&1

echo
echo "########## C. /props 实测：服务端认为的默认采样 ##########"
curl -s -m 8 http://127.0.0.1:8090/props 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
p=d.get('default_generation_settings',{}).get('params',{})
print(json.dumps(p, ensure_ascii=False, indent=2))
" 2>&1
