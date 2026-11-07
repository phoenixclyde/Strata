cd /home/albus/strata166/tmp
pkill -f w828_ab.sh 2>/dev/null || true
for a in b154n b154na b154na b154n; do rm -f /home/albus/strata166/data/w828_ab_$a.txt; done
setsid nohup bash /home/albus/strata166/tmp/w828_ab.sh b154n b154na b154na b154n > /home/albus/strata166/data/w828_ab2.log 2>&1 < /dev/null &
sleep 20
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -6 /home/albus/strata166/data/w828_ab2.log
