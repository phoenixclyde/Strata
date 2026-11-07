#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 移走 marker（保留证据，不删）==="
docker exec $C mv /data/strata-trace /data/strata-trace.off-w920
docker exec $C sh -c 'ls -la /data/strata-trace* 2>/dev/null'

echo "=== 确认 trace 立即停止（发一个极小请求后看有无新 trace 行）==="
BASE=$(docker exec $C grep -c "strata trace:" $LOG)
echo "移走前 trace 行数: $BASE"
curl -s -m 60 http://127.0.0.1:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"x","messages":[{"role":"user","content":"hi"}],"max_tokens":8,"temperature":0}' > /dev/null
sleep 2
NOW=$(docker exec $C grep -c "strata trace:" $LOG)
echo "移走后 trace 行数: $NOW  (增量 $((NOW-BASE)))"
