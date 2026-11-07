echo "=== STRATA_LOGPOS in the engine ==="
cd /home/albus/strata166/src028
grep -rn "STRATA_LOGPOS" src include | head -8
echo
echo "=== TOPK / logpos file format ==="
grep -rn "LOGPOS" src/program/generate.cpp | head -12
echo
echo "=== existing KL tools ==="
ls -la /home/albus/strata166/tmp/*kl*.py /home/albus/strata166/tmp/*logpos* 2>/dev/null | head
ls -la /home/albus/strata166/data/*logpos* 2>/dev/null | tail -5
