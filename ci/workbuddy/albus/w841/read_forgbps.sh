set +e
cd /home/albus/strata166/gfx906
echo "=== pcie_frac_for_gbps 2270,2330 ==="
sed -n '2270,2330p' src/program/generate.cpp
echo
echo "=== PcieAuto 定义 ==="
grep -rn "struct PcieAuto\|class PcieAuto" src include | head
