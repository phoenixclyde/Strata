#!/bin/bash
S=/home/albus/strata166/src028/src/core/arch_defaults.cpp
echo "=== gfx1151 表：从 guard 到 return 之间 ==="
sed -n '55,110p' $S | grep -n 'STRATA_\|return\|^    }' | sed 's/^/  /'
echo
echo "  条目数（该段 {\"STRATA_）："
sed -n '55,110p' $S | grep -c '{"STRATA_'
echo
echo "=== 125-175 段（HC_UPMIX 属于哪个表） ==="
sed -n '125,175p' $S | grep -n 'STRATA_\|gfx12\|gfx1151\|IGPU_PROMPT_SET\|return' | sed 's/^/  /'
