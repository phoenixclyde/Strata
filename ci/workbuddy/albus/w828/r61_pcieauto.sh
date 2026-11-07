cd /home/albus/strata166/src028
echo "=== pcie_frac_auto / PcieAuto ==="
grep -rn "pcie_frac_auto\|PcieAuto\|pcie auto" src include | head -16
echo
echo "=== the auto refinement code ==="
F=$(grep -rln "struct PcieAuto\|class PcieAuto" src include | head -1); echo "file: $F"
[ -n "$F" ] && sed -n '1,80p' "$F"
