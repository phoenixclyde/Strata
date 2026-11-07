echo "=== fork evidence in the tc engine log ==="
grep -aiE "fork|sh_stream|shared expert.*stream|SH_STREAM" /home/albus/strata166/data/w828_tc.log 2>/dev/null | head -8 | cut -c1-190
echo "=== how many times the two logs mention it ==="
for a in ta tc; do printf "%s: " "$a"; grep -aic "sh_stream\|fork" /home/albus/strata166/data/w828_$a.log 2>/dev/null; done
echo "=== full tc decode-timing line (the tail fields matter) ==="
grep -a "strata decode timing" /home/albus/strata166/data/w828_tc.log | tail -1 | cut -c1-420
echo
echo "=== full ta decode-timing line ==="
grep -a "strata decode timing" /home/albus/strata166/data/w828_ta.log | tail -2 | head -1 | cut -c1-420
