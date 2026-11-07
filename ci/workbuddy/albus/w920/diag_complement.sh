#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 本次 run 的 FileExpertSource / RAM 全段 ==="
docker exec $C sh -c "tail -900 $LOG | grep -nE 'FileExpertSource|RAM budget|resident RAM mode|expert arena|hugepage|PLE table|memory guard|expert cache|slots' | cut -c1-170"

echo
echo "=== 与上一次 run（旧容器）同一段的对比 ==="
docker exec $C sh -c "grep -n 'RAM budget' $LOG | tail -3 | cut -c1-170"

echo
echo "=== 本次启动行号定位 ==="
docker exec $C sh -c "grep -n 'engine started' $LOG | tail -2 | cut -c1-100"
