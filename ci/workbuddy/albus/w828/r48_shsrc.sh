cd /home/albus/strata166/src028
echo "=== STRATA_SH_STREAM: definition / use sites ==="
grep -rn "STRATA_SH_STREAM" src include 2>/dev/null | head -20
echo
echo "=== shared expert stream: kernel / launch side ==="
grep -rn "sh_stream" src include 2>/dev/null | head -20
