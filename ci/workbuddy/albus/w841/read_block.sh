set +e
cd /home/albus/strata166/gfx906
echo "=== generate.cpp 4240-4310 ==="
sed -n '4240,4310p' src/program/generate.cpp
echo
echo "=== generate.cpp 2170,2215 ==="
sed -n '2170,2215p' src/program/generate.cpp
echo
echo "=== defaults_026.hpp 20,60 ==="
sed -n '20,60p' include/strata/core/defaults_026.hpp
echo
echo "=== 该函数定义头（往上找签名） ==="
awk 'NR>=4180 && NR<=4255' src/program/generate.cpp | grep -n "static\|^[a-zA-Z].*(" | head -20
