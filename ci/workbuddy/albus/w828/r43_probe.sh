echo "=== memory channels ==="
sudo -n dmidecode -t memory 2>/dev/null | grep -E "Size:|Locator:|Speed:|Type:" | head -30 || echo "(no sudo)"
echo "--- lscpu mem ---"
lscpu | grep -iE "model name|core|thread|numa node" | head -8
echo "=== DECODE_TIMING format in source ==="
grep -rn "decode timing" /home/albus/strata166/src028/src/program/generate.cpp | head -6
echo "=== adapt implementation ==="
grep -rn "adapt_every\|adapt_swaps\|adapt_decay" /home/albus/strata166/src028/src/program/generate.cpp | head -12
echo "=== hit rate lines from the two ABBA arms ==="
for a in b154n b154na; do
  echo "-- $a"
  grep -aoE "expert cache [0-9.]+% hit" /home/albus/strata166/data/w828_ab_$a.txt 2>/dev/null | head -12
done
