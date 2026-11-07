S=/home/albus/strata166/src028
echo "=== CMakeLists 2125-2160 ==="
sed -n '2125,2160p' "$S/CMakeLists.txt"
echo
echo "=== CMakeLists 2225-2260 (the strata_kq library) ==="
sed -n '2225,2260p' "$S/CMakeLists.txt"
echo
echo "=== what the configure said about MMQ in build-028.log (first 40 hits) ==="
grep -nE "MMQ|KQUANT|strata_kq" "$S/build-028.log" 2>/dev/null | head -20
