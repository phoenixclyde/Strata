cd /home/albus/strata166/tmp
pkill -f w828_ab.sh 2>/dev/null || true
rm -f /home/albus/strata166/data/w828_ab_a153.txt /home/albus/strata166/data/w828_ab_b154n.txt
setsid nohup bash /home/albus/strata166/tmp/w828_ab.sh a153 b154n > /home/albus/strata166/data/w828_ab.log 2>&1 < /dev/null &
sleep 25
echo "--- launcher ---"
cat /home/albus/strata166/data/w828_ab.log | head -20
echo "--- containers ---"
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
