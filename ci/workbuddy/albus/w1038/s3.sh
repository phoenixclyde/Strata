#!/bin/bash
S=/home/albus/strata166/pr/k10
echo "=== A. bytes_per_cell 实现 ==="
grep -rn "kv_q8_bytes_per_cell\|kv_q4_bytes_per_cell\|kv_hybrid_bytes_per_cell" $S/src --include=*.cpp --include=*.hpp --include=*.cu --include=*.cuh | head -12
echo "=== B. 定义体 ==="
grep -rn -A14 "int64_t kv_q8_bytes_per_cell" $S/src/kernels/*.cpp $S/src/kernels/*.cu 2>/dev/null | head -40
echo "=== C. 生产日志 KV 分配 ==="
grep -iE "kv pool|kv cells|cells of|qsa layers|kv bytes|kv: |kv_hybrid" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -12
echo "=== D. bench 里 kv 结果目录 ==="
ls -d $S/bench/results/*kv* 2>/dev/null
