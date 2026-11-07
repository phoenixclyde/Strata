#!/bin/bash
S=/home/albus/strata166/src028
echo "=== [1] strata_tune 的请求字段与解析 ==="
grep -n "strata_tune\|tune" $S/serve/server.py | head -20
echo
echo "--- 上下文：1430-1500 ---"
sed -n '1430,1500p' $S/serve/server.py
echo
echo "=== [2] 引擎侧怎么用 tune（是不是每条请求都生效） ==="
grep -rn "pcie_frac\|spec_min_p" $S/serve/server.py | head -20
