#!/bin/bash
set -u
C="docker exec strata166-407"
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "########## A. 启动段的显存规划（VRAM 预算/KV 预留） ##########"
$C sh -c "grep -inE 'VRAM|budget|reserve|kv ensured|kv pool|pages|prealloc|kv_grow' $LOG | head -40" 2>&1 | cut -c1-190

echo
echo "########## B. kv ensured 的形态（是否按需） ##########"
$C sh -c "grep -c 'kv ensured' $LOG; grep -m3 -A2 'kv ensured' $LOG" 2>&1 | cut -c1-200

echo
echo "########## C. --max-context 与 KV 页数关系 ##########"
$C sh -c "grep -inE 'max.context|max_cells|n_pages|page_size|slots' $LOG | head -12" 2>&1 | cut -c1-190
