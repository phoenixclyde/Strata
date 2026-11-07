#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log
docker exec $C sh -c "grep -n 'trace:' $LOG | tail -4 | cut -c1-170"
echo "--- 日志尾部 6 行 ---"
docker exec $C sh -c "tail -6 $LOG | cut -c1-150"
echo "--- marker 现状 ---"
docker exec $C sh -c "ls -la /data/strata-trace* /src/.strata-trace 2>&1 | head -4"
echo "--- 引擎 cwd ---"
docker exec $C sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); readlink /proc/$P/cwd'
