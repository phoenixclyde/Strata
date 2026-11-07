#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 关掉 trace marker（改名保留，需要时 touch 即开）==="
docker exec $C mv /data/strata-trace /data/strata-trace.off
docker exec $C sh -c 'ls -la /data/strata-trace* 2>&1'

echo
echo "=== 引擎线程构成（29 个线程是谁）==="
docker exec $C sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); for t in /proc/$P/task/*; do cat $t/comm 2>/dev/null; done | sort | uniq -c | sort -rn | head -12'

echo
echo "=== vision 塔的内存/线程线索 ==="
docker exec $C sh -c "grep -inE 'strata-vision|vision:' $LOG | tail -4 | cut -c1-140"

echo
echo "=== KV 池 / cells / context 分配 ==="
docker exec $C sh -c "grep -inE 'kv pool|kv cells|cells allocated|context .*tokens|KV ' $LOG | tail -6 | cut -c1-150"

echo
echo "=== 显存全貌（最终态）==="
docker exec $C sh -c "grep -inE 'VRAM free|borrows|MiB of weights|expert cache' $LOG | tail -6 | cut -c1-150"
