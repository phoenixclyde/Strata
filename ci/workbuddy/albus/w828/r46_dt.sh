date +%H:%M:%S
ls -la /home/albus/strata166/data/w828_ta.log 2>/dev/null
echo "--- decode timing lines (ta) ---"
grep -a "strata decode timing" /home/albus/strata166/data/w828_ta.log 2>/dev/null | tail -4 | cut -c1-280
echo "--- count ---"
grep -ac "strata decode timing" /home/albus/strata166/data/w828_ta.log 2>/dev/null
echo "--- tb progress ---"
tail -6 /home/albus/strata166/data/w828_ab2_tb.txt 2>/dev/null | cut -c1-180
