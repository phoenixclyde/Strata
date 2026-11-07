#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 本次 run 起点 ==="
docker exec $C sh -c "grep -n 'engine started' $LOG | tail -1 | cut -c1-80"

echo
echo "=== 三个开关的任何提示（含 not used / needs）==="
docker exec $C sh -c "awk 'NR>110700' $LOG | grep -inE 'GROUP_SCRATCH|ROUTED_STREAM|HC_REGION|not used|needs MMQ' | cut -c1-180" 

echo
echo "=== prefill 布局相关：fused / FP16 / MMQ ==="
docker exec $C sh -c "awk 'NR>110700' $LOG | grep -inE 'fused|FP16 fallback|pf_wmma|every layer|layout' | head -10 | cut -c1-170"

echo
echo "=== 进程 env 是否带三项 ==="
docker exec $C sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); tr "\0" "\n" < /proc/$P/environ | grep -E "PF_GROUP|ROUTED|HC_REGION"'

echo
echo "=== 二进制 md5 确认 ==="
docker exec $C sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); md5sum /proc/$P/exe | cut -c1-32'
