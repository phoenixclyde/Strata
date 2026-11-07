cd /home/albus/strata166/src028
echo "=== STRATA_SH_FORK_LATE ==="
grep -rn "SH_FORK_LATE" src include | head -10
echo
echo "=== the fork-late window in verify.cpp (around 2045) ==="
sed -n '2038,2060p' src/core/verify.cpp
echo "=== and around 2125-2175 (the late fork) ==="
sed -n '2120,2175p' src/core/verify.cpp
