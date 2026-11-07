#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 1. 启动期显存/内存分配全清单（最后一次启动）==="
docker exec $C sh -c "awk 'NR>=108800 && /MiB|GiB|slots|context|cell/ {print NR\": \"\$0}' $LOG | grep -viE 'trace:' | cut -c1-160 | head -30"

echo
echo "=== 2. max-context 262144 是否真被分配（找 context / cells 相关）==="
docker exec $C sh -c "grep -inE 'context|kv cells|cell budget|262144|131072' $LOG | grep -viE 'trace:|strata serve: prompt' | tail -8 | cut -c1-150"

echo
echo "=== 3. vision 是否被模型使用（有无图片请求）==="
docker exec $C sh -c "grep -icE 'image|picture' $LOG; grep -icE 'strata-vision: encoded|image tokens' $LOG"

echo
echo "=== 4. conversation-cache 4 GiB 是否落账 ==="
docker exec $C sh -c "grep -inE 'conversation cache|4096 MiB|conversation-cache' $LOG | tail -5 | cut -c1-150"
