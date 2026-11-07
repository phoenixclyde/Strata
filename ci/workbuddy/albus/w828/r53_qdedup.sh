cd /home/albus/strata166/src028
echo "=== qdedup default ==="
grep -rn "g_qdedup" src/core/verify.cpp | head -5
sed -n "$(grep -n 'bool g_qdedup' src/core/verify.cpp | head -1 | cut -d: -f1),+10p" src/core/verify.cpp
echo "=== ar_on (does it disable the late fork?) ==="
sed -n "$(grep -n 'bool ar_on' src/core/verify.cpp | head -1 | cut -d: -f1),+12p" src/core/verify.cpp
