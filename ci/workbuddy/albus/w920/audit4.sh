#!/bin/bash
C=strata166-407
echo "=== 精确检查两个 marker 路径 ==="
docker exec $C sh -c 'for f in /data/strata-trace /src/.strata-trace; do if [ -e "$f" ]; then echo "EXISTS  $f  size=$(stat -c%s "$f") mtime=$(stat -c%y "$f")"; else echo "absent  $f"; fi; done'
echo
echo "=== /data 下所有 strata* 文件 ==="
docker exec $C sh -c 'ls -la --time-style=+%Y-%m-%d_%H:%M /data/strata* 2>/dev/null | head -12'
echo
echo "=== /src 下 .strata* 与隐藏文件 ==="
docker exec $C sh -c 'ls -la /src/.strata* 2>/dev/null; ls -a /src | grep -i strata | head'
echo
echo "=== window 那 17908 行是什么 ==="
docker exec $C sh -c 'grep -m3 "strata trace: window" /data/strata-huihui-ud-iq4_xs.log | cut -c1-160'
echo
echo "=== 源码里 tr(\"window\") 的调用点 ==="
cd ~/strata166/pr/strata-fork
grep -rn 'tr("window' --include=*.cpp src/ | head -5
echo
echo "=== 每行 dt 的 stat 成本：tr 里 trace_on 是每行调用吗 ==="
grep -c "trace_on()" src/program/generate.cpp
