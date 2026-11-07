L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
date +%H:%M:%S
echo "--- arm medians from the driver log ---"
grep -aE "=== ARM2|MEDIAN|p[0-9]  ptok" /home/albus/strata166/data/w828_spec_ab.log | cut -c1-120
echo
echo "--- all decode-timing lines, in order (4 per arm: warm + p0 p1 p2) ---"
grep -an "strata decode timing" "$L" | tail -20 | sed -E 's/strata decode timing: ([0-9]+) windows, avg T ([0-9.]+), ([0-9.]+) tokens\/window, ([0-9.]+) ms\/window.*/w=\1 T=\2 tok\/win=\3 ms\/win=\4/' | cut -c1-160
echo
echo "--- spec depth lines (4 per arm) ---"
grep -a "strata serve: spec depth" "$L" | tail -20 | cut -c1-160
echo
echo "--- reached windows / max T mentions ---"
grep -a "reached\|window rows\|rows)" "$L" | tail -5 | cut -c1-160
