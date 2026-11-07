set +e
cd /home/albus/strata166/gfx906
echo "### [1] 四道门的实际行号（sed 现场）"
sed -n '2150,2160p;2194,2204p;4250,4256p;4288,4294p' src/program/generate.cpp | cat -n
echo
echo "### [2] decode_defaults_arch_ok 的调用点 + 每处所在块"
grep -n "decode_defaults_arch_ok()" src/program/generate.cpp
echo
echo "### [3] 2111/2124/2140/4948 这几行到底是什么"
for n in 2111 2124 2140 2153 4948 4208; do printf '%s: ' $n; sed -n "${n}p" src/program/generate.cpp | cut -c1-120; done
echo
echo "### [4] pcie_auto_fork_arch_ok 调用点"
grep -n "pcie_auto_fork_arch_ok" src/program/generate.cpp
