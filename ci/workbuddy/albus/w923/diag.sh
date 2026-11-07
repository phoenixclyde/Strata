#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 1. 引擎进程 env 是否带 HSA_TOOLS_LIB ==="
docker exec $C sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); echo pid=$P; tr "\0" "\n" < /proc/$P/environ | grep -E "HSA_TOOLS|ROCPROF" | head -8'

echo
echo "=== 2. 库路径是否存在 ==="
docker exec $C sh -c 'ls -l /opt/rocm/lib/rocprofiler-sdk/librocprofiler-sdk-tool.so 2>&1; ls -l /opt/rocm/lib/librocprofiler-sdk-tool.so 2>&1'

echo
echo "=== 3. 日志里的 profiler 线索 ==="
docker exec $C sh -c "tail -300 $LOG | grep -inE 'rocprof|profiler|tool|HSA_TOOLS' | head -10 | cut -c1-170"

echo
echo "=== 4. serve 层是否过滤环境 ==="
docker exec $C sh -c "grep -n 'subprocess\|env=' /src/serve/server.py | head -12"
