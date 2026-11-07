#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 1. trace 行数 ==="
docker exec $C grep -c "strata trace:" $LOG

echo "=== 2. trace 种类分布 ==="
docker exec $C sh -c "grep -o 'strata trace: [a-z ]*' $LOG | sort | uniq -c | sort -rn | head -12"

echo "=== 3. vision / picture 行样本 ==="
docker exec $C sh -c "grep -iE 'vision|picture' $LOG | tail -3 | cut -c1-140"

echo "=== 4. 源码里 strata trace 的来源 ==="
cd ~/strata166/pr/strata-fork || exit 1
grep -rn "strata trace:" --include=*.cpp --include=*.hpp src/ include/ | head -6

echo "=== 5. vision 在源码里的消费点 ==="
grep -rn "opt_vision\|\"--vision\"\|vision_load\|vision_tower" --include=*.cpp --include=*.hpp src/ include/ | head -8

echo "=== 6. 日志里所有输出类别（按前缀统计）==="
docker exec $C sh -c "grep -oE '^strata [a-z]+:' $LOG | sort | uniq -c | sort -rn | head -15"
