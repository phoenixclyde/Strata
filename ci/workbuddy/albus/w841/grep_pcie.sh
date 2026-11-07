set +e
cd /home/albus/strata166/gfx906
echo "=== grep -rn PCIE_FRAC (src) ==="
grep -rn "PCIE_FRAC" src include 2>/dev/null
echo
echo "=== grep -rn pcie_frac_auto ==="
grep -rn "pcie_frac_auto" src include 2>/dev/null | head -40
echo
echo "=== grep -rn pcie_frac (general) ==="
grep -rn "pcie_frac" src include 2>/dev/null | head -60
