#!/bin/bash
S=/home/albus/strata166/src028
echo "=== [1] --pool-workers 的帮助/默认 ==="
grep -n "pool-workers" $S/src/program/generate.cpp | head -8
echo
echo "--- 默认值与解释 ---"
grep -n "pool_workers" $S/src/program/generate.cpp | head -20
echo
echo "=== [2] 生产实际起了多少 worker（日志） ==="
docker exec strata166-407 bash -lc 'grep -aiE "pool workers|CPU pool|CPU workers" /data/strata-huihui-ud-iq4_xs.log | tail -4 | cut -c1-170' 2>&1
echo
echo "=== [3] calibrate 当初扫过哪些值 ==="
grep -n "pool" $S/tools/calibrate.py | head -10
