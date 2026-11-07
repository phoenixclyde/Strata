date +%H:%M:%S
for a in ta tb; do
  echo "===== $a ($(stat -c%s /home/albus/strata166/data/w828_$a.log 2>/dev/null) B)"
  grep -a "strata decode timing" /home/albus/strata166/data/w828_$a.log 2>/dev/null | sed -E 's/.*windows, avg T ([0-9.]+), ([0-9.]+) tokens\/window, ([0-9.]+) ms\/window.*/\1 \2 \3/' | tail -6
  echo "  full last line:"
  grep -a "strata decode timing" /home/albus/strata166/data/w828_$a.log 2>/dev/null | tail -1 | cut -c1-200
  echo "  tok/s from the arm log:"
  grep -aE "MEDIAN|p[0-9] .*tok/s" /home/albus/strata166/data/w828_ab2_$a.txt 2>/dev/null | tail -5 | cut -c1-110
  echo "  swaps/window:"
  grep -a "strata decode timing" /home/albus/strata166/data/w828_$a.log 2>/dev/null | grep -oE "[0-9.]+ swaps/window" | tail -3
done
