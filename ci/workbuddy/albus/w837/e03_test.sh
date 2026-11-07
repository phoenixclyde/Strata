#!/bin/bash
# W837: the test harness shape + what bitwise evidence we already have
W=/home/albus/strata166/gfx906
cd $W || exit 1
echo "=== A. arch_defaults_test.cpp : structure (first 70 lines) ==="
sed -n '1,70p' src/core/arch_defaults_test.cpp | cut -c1-165
echo
echo "=== B. how the test is registered ==="
grep -rn "arch_defaults_test" CMakeLists.txt src/CMakeLists.txt 2>/dev/null | head -4
echo
echo "=== C. is the test built/run by default? ==="
grep -rn "arch_defaults" CMakeLists.txt 2>/dev/null | head -4
