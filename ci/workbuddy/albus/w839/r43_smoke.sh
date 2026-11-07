#!/bin/bash
# W839-43 终检：同步一致性 + 生产健康 + 实请求
date +%H:%M:%S
echo "=== 分支/同步 ==="
git -C /home/albus/strata166/gfx906 log -1 --format='  %h %s' | cut -c1-90
git -C /home/albus/strata166/gfx906 status --porcelain | head -3
bash /home/albus/strata166/tmp/sync_gfx906.sh --check 2>&1 | grep -E 'same|applied|DIFF|drift' | tail -12
echo
echo "=== 生产 ==="
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
python3 -c "import json;c=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('exe',c['exe'],'args',len(c['args']),'env',len(c['env']))"
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 100; echo
echo "=== 实请求（24 tok） ==="
curl -s --max-time 120 http://127.0.0.1:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"用一句话说明海水的颜色为什么偏蓝。"}],"max_tokens":64,"temperature":0,"stream":false}' \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
u=(d.get('usage') or {})
ch=(d.get('choices') or [{}])[0]
msg=(ch.get('message') or {})
txt=(msg.get('content') or msg.get('reasoning_content') or '')
print('  completion_tokens=%s  text[:60]=%s' % (u.get('completion_tokens'), txt[:60].replace(chr(10),' ')))
"
echo "=== 引擎侧最近两条 timing 行 ==="
grep -aE 'prompt [0-9]+ tokens = ' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -2 | cut -c1-150
