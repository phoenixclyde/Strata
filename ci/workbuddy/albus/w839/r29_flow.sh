#!/bin/bash
# W839-29 看新调用块所在的控制流 + tuned 表门控
S=/home/albus/strata166/src028
echo "=== generate.cpp 3395-3450 ==="
sed -n '3395,3450p' $S/src/program/generate.cpp
echo
echo "=== 这段属于哪个函数（往上找顶层函数头） ==="
N=3436
for i in $(seq $N -1 3000); do
  line=$(sed -n "${i}p" $S/src/program/generate.cpp)
  case "$line" in
    "int main"*|"static int"*|"int run"*) echo "  $i: $line"; break;;
  esac
done
echo
echo "=== arch_defaults.cpp 190-226（tuned 门控）==="
sed -n '190,226p' $S/src/core/arch_defaults.cpp
