set +e
echo "##### FILE w842_simt2_20261031_181616.txt"
cat /home/albus/strata166/data/w842_simt2_20261031_181616.txt 2>/dev/null
echo "##### FILE w842_b_182919.txt"
cat /home/albus/strata166/data/w842_b_182919.txt 2>/dev/null
echo "##### FILE param_register.bak? "
ls -l /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json.bak-w839 2>/dev/null | head -2
ls -l /home/albus/strata166/params/ 2>/dev/null | head -6
echo "##### GREP SIMT2 banner (with line numbers)"
grep -an "STRATA_SELECT_SIMT=2), tiles 32/128" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "##### GREP last 6 qsa select with line numbers"
grep -an "qsa select" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -8
echo "##### GATE"
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -20
