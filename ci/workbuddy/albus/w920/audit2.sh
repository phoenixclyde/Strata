#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log
cd ~/strata166/pr/strata-fork || exit 1

echo "=== A1. strata trace: window 的打印点 ==="
grep -rn "strata trace: window" --include=*.cpp --include=*.cu --include=*.hpp src/ | head -4

echo "=== A2. 该文件里 trace 的门条件（trace 开/关怎么判）==="
grep -rn "trace_on\|g_trace\|STRATA_TRACE\|trace_ = \|trace_enabled" --include=*.cpp --include=*.hpp src/program/generate.cpp src/program/*.hpp include/strata/program/*.hpp 2>/dev/null | head -12

echo "=== A3. STRATA_TRACE 全树命中 ==="
grep -rn "STRATA_TRACE" --include=*.cpp --include=*.cu --include=*.hpp --include=*.h src/ include/ | head -8

echo "=== B1. vision 加载行上下文 ==="
docker exec $C sh -c "grep -n -B3 -A6 'strata-vision: model files loaded' $LOG | cut -c1-140 | head -20"

echo "=== B2. 进程线程数与 RSS ==="
docker exec $C sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); echo "threads=$(ls /proc/$P/task | wc -l)  RSS=$(awk "/VmRSS/{print \$2/1048576\" GiB\"}" /proc/$P/status)"'
