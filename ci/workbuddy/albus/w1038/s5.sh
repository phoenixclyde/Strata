#!/bin/bash
S=/home/albus/strata166/pr/k10
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== A. bytes_per_cell 定义（无 include 过滤）==="
grep -rn "kv_q8_bytes_per_cell" $S --include=* 2>/dev/null | grep -v "\.o:" | head -10
echo
echo "=== B. n_qsa_layers 定义 ==="
grep -rn "n_qsa_layers" $S/src --include=*.hpp --include=*.h --include=*.cpp | head -8
echo
echo "=== C. 层类型判定（qsa vs gdn）==="
grep -rn "qsa_idx\|is_qsa\|full_attn\|attn_every\|% 4" $S/src/core/model*.cpp $S/src/core/model*.hpp 2>/dev/null | head -12
echo
echo "=== D. 启动 banner 里带 MiB/GiB 的行（近 60 条）==="
grep -nE "MiB|GiB" $L | tail -30
