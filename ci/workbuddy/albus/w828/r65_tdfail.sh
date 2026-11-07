date +%H:%M:%S
echo "=== td arm log ==="
cat /home/albus/strata166/data/w828_ab2_td.txt 2>/dev/null | tail -30 | cut -c1-190
echo "=== td engine log (last 25) ==="
tail -25 /home/albus/strata166/data/w828_td.log 2>/dev/null | cut -c1-190
echo "=== ab4 driver ==="
tail -12 /home/albus/strata166/data/w828_ab4.log 2>/dev/null | cut -c1-170
