#!/bin/bash
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== count of real decode stage lines ==="
grep -c "strata decode GPU stages" "$L"
echo "=== last 3 (real, with digits) ==="
grep -n "strata decode GPU stages" "$L" | tail -3 | cut -c1-4000
echo "=== last 5 summary lines ==="
grep -n "strata serve: prompt .*generated" "$L" | tail -5 | cut -c1-300
echo "=== native head line occurrences ==="
grep -n "native Q5_K head\|native Q8_0 head\|native head" "$L" | tail -5 | cut -c1-200
