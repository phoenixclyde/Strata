#!/bin/bash
set -u
C=strata166-407
echo "=== 1) server 侧：fatal GPU 记账行 ==="
docker exec $C sh -lc 'grep -n "fatal error\|fatal GPU\|of 3 allowed\|the engine had stopped (exit code 3)" /data/strata-huihui-ud-iq4_xs.log | tail -10' | cut -c1-230

echo
echo "=== 2) 引擎侧 stderr 的最后一句 ==="
docker exec $C sh -lc 'grep -n "strata serve: fatal GPU error" /data/strata-huihui-ud-iq4_xs.log | tail -3' | cut -c1-200

echo
echo "=== 3) 引擎退出码 ==="
docker exec $C sh -lc 'grep -n "engine had stopped" /data/strata-huihui-ud-iq4_xs.log | tail -3' | cut -c1-200

echo
echo "=== 4) 重启后的引擎指纹（应为 cf2ba243，新 pid） ==="
docker exec $C sh -lc 'P=$(pgrep -f "strata-0.1.55t --serve" | head -1); echo pid=$P; md5sum /proc/$P/exe | cut -c1-32'

echo
echo "=== 5) 标志文件已生成 ==="
docker exec $C ls -l /data/w936/fired.flag 2>&1 | head -1

echo
echo "=== 6) 注入后是否又注入过（应只 1 次） ==="
docker exec $C sh -lc 'grep -c "injected (STRATA_INJECT_FATAL)" /data/strata-huihui-ud-iq4_xs.log'
