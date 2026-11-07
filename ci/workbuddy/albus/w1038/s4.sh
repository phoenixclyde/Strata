#!/bin/bash
S=/home/albus/strata166/pr/k10
echo "=== A. 找 bytes_per_cell 定义（全树）==="
grep -rn "bytes_per_cell" $S/src --include=*.cu --include=*.cuh --include=*.cpp --include=*.hpp | head -20
echo
echo "=== B. 定义体附近 ==="
for f in $(grep -rln "kv_q8_bytes_per_cell" $S/src); do
  echo "--- $f"
  grep -n -A18 "int64_t kv_q8_bytes_per_cell" $f | head -30
done
echo
echo "=== C. QSA 层数 / 混合层 ==="
grep -rn "n_qsa\|qsa_layers\|n_attn_layers\|is_qsa" $S/src/core/*.cpp $S/src/core/*.hpp 2>/dev/null | head -12
echo
echo "=== D. 日志里的 KV/显存计划 ==="
grep -iE "kv.*(GiB|MiB|GB)|(GiB|MiB).*kv|cells\b" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -14
