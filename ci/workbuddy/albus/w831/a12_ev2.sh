#!/bin/bash
S=/home/albus/strata166/src028
echo "=== [1] 模型到底几层（expert 实例 / 每层专家数） ==="
F=/home/albus/strata166/data/packs/ud-q4_k_xl/native_experts.txt
ls -la $F 2>/dev/null || echo "  (check other path)"
if [ -f "$F" ]; then
  head -1 "$F"
  echo "  lines=$(wc -l < $F)"
  echo "  --- distinct layer ids (col1) ---"
  awk 'NR>1{print $1}' "$F" | sort -n | uniq | wc -l
  echo "  --- distinct expert ids in layer 0 ---"
  awk 'NR>1 && $1==0{print $2}' "$F" | sort -n | uniq | wc -l
  echo "  --- first 3 / last 3 rows ---"
  head -4 "$F"; echo "  ..."; tail -2 "$F"
fi
echo
echo "--- engine log: layer count hints ---"
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
docker exec strata166-407 bash -lc "grep -aiE 'n_layer|layers|experts per|per layer|24576|30720' $L 2>/dev/null | head -8" 2>&1
echo
echo "=== [2] arch_defaults.cpp gfx1151 表：到底几项 ==="
awk 'NR>=50 && NR<=100' $S/src/core/arch_defaults.cpp | grep -n 'STRATA_[A-Z0-9_]*":' | sed 's/^/   /'
echo "   --- 该段 STRATA_ 条目总数 ---"
awk 'NR>=50 && NR<=100' $S/src/core/arch_defaults.cpp | grep -c '{"STRATA_'
echo
echo "=== [3] gfx12 段（含 HC_UPMIX） ==="
awk 'NR>=20 && NR<=50' $S/src/core/arch_defaults.cpp | grep -n '{"STRATA_\|gfx12\|gfx1151' | sed 's/^/   /'
