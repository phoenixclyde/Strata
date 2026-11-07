set +e
cd /home/albus/strata166
echo "=== PARAM_REGISTER: P227 / pcie ==="
grep -niE "P227|pcie-frac|pcie_frac" /home/albus/strata166/*/params/PARAM_REGISTER.tsv 2>/dev/null | head -20
find /home/albus/strata166 -name PARAM_REGISTER.tsv -maxdepth 4 2>/dev/null
