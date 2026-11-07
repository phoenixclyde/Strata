S27=/home/albus/strata166/src0271
S28=/home/albus/strata166/src028
echo "=== files carrying our markers (W7xx/W8xx/R5-A) in src0271 ==="
grep -rlE "W7[0-9][0-9]|W8[0-9][0-9]|\[R5-A\]|W[0-9]{3} local" "$S27/src" "$S27/include" "$S27/CMakeLists.txt" "$S27/serve" "$S27/cmake" 2>/dev/null | sed "s#$S27/##" | sort > /tmp/m27.txt
grep -rlE "W7[0-9][0-9]|W8[0-9][0-9]|\[R5-A\]|W[0-9]{3} local" "$S28/src" "$S28/include" "$S28/CMakeLists.txt" "$S28/serve" "$S28/cmake" 2>/dev/null | sed "s#$S28/##" | sort > /tmp/m28.txt
wc -l < /tmp/m27.txt | xargs echo "  src0271 files:"
wc -l < /tmp/m28.txt | xargs echo "  src028 files:"
echo
echo "--- present in src0271 but NOT in src028 (candidate losses) ---"
comm -23 /tmp/m27.txt /tmp/m28.txt | sed 's/^/  LOST  /'
echo
echo "--- in both ---"
comm -12 /tmp/m27.txt /tmp/m28.txt | sed 's/^/  ok    /'
echo
echo "=== per-file marker counts (0271 vs 028) ==="
while read -r f; do
  a=$(grep -coE "W7[0-9][0-9]|W8[0-9][0-9]|\[R5-A\]" "$S27/$f" 2>/dev/null || echo 0)
  b=$(grep -coE "W7[0-9][0-9]|W8[0-9][0-9]|\[R5-A\]" "$S28/$f" 2>/dev/null || echo 0)
  ms=$(grep -oE "W[0-9]{3}[a-z]?|\[R5-A\]" "$S27/$f" 2>/dev/null | sort -u | tr '\n' ' ')
  printf '  %-52s %3s -> %3s   %s\n' "$f" "$a" "$b" "$ms"
done < /tmp/m27.txt
