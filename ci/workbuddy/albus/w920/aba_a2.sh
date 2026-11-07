#!/bin/bash
C=strata166-407
echo "=== A2 臂：把 marker 放回（恢复 trace 常开）==="
docker exec $C mv /data/strata-trace.off-w920 /data/strata-trace
docker exec $C sh -c 'ls -la /data/strata-trace'
BASE=$(docker exec $C grep -c "trace:" /data/strata-huihui-ud-iq4_xs.log)
echo "放回前 trace 行数: $BASE"
echo "=== 立刻测 A2 ==="
cd ~ && python3 ~/strata166/ci/bench_pair.py --prefill-words 4100 --n 6 --decode-tokens 256 2>&1 | tail -8
NOW=$(docker exec $C grep -c "trace:" /data/strata-huihui-ud-iq4_xs.log)
echo "A2 期间 trace 增量: $((NOW-BASE))"
