#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 最后一次启动的行号 ==="
docker exec $C sh -c "grep -n 'engine started' $LOG | tail -1 | cut -c1-90"

echo
echo "=== 最后 3 次 run 各自是 file cache 还是 page-locked ==="
docker exec $C sh -c "grep -nE 'expert arena read through|page-locked cache complement|mapped pinned|resident RAM mode' $LOG | tail -8 | cut -c1-150"

echo
echo "=== 当前 run 的 RAM 预算相关 ==="
docker exec $C sh -c "tail -800 $LOG | grep -E 'RAM budget|FileExpertSource|memory guard|available' | cut -c1-170"

echo
echo "=== profile 文件时间戳（是否被上次运行改写）==="
docker exec $C sh -c 'ls -la --time-style=+%Y-%m-%d_%H:%M /data/profiles/q4kxl-learned.bin /src/data/expert-profile.bin 2>/dev/null'
