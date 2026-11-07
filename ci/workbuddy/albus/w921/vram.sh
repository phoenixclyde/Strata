#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 本次 run（三开关开）的显存/借用 ==="
docker exec $C sh -c "awk 'NR>110993' $LOG | grep -E 'borrows|VRAM free with everything|expert cache [0-9]+ slots|window up to' | head -6 | cut -c1-150"

echo
echo "=== 上一次 run（a97f4479，无三开关）同一段，做对比 ==="
docker exec $C sh -c "awk 'NR>108911 && NR<110993' $LOG | grep -E 'borrows|VRAM free with everything|expert cache [0-9]+ slots|window up to' | head -6 | cut -c1-150"

echo
echo "=== 更早一次（同二进制 a97f4479，回滚后那次 110639）==="
docker exec $C sh -c "awk 'NR>110622 && NR<110993' $LOG | grep -E 'borrows|VRAM free with everything' | head -3 | cut -c1-150"
