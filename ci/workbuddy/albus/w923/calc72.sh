#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 1. 历史上出现过的 expert cache 槽数（去重）==="
docker exec $C sh -c "grep -oE 'expert cache [0-9]+ slots, [0-9.]+ GiB' $LOG | sort | uniq -c | sort -rn | head -10"

echo
echo "=== 2. 槽数与 borrow 的对应（最近 6 次启动）==="
docker exec $C sh -c "grep -nE 'expert cache [0-9]+ slots|prompt path borrows' $LOG | tail -12 | cut -c1-130"

echo
echo "=== 3. 当前 decode 命中率的量级 ==="
docker exec $C sh -c "grep -oE 'decode expert cache hit rate: [0-9.]+%' $LOG | tail -8"

echo
echo "=== 4. reserve 与实际 VRAM free 的关系 ==="
docker exec $C sh -c "grep -E 'expert cache auto:|VRAM free with everything' $LOG | tail -4 | cut -c1-170"
