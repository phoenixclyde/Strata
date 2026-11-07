cd /home/albus/strata166/tmp
pkill -f w828_ab2.sh 2>/dev/null || true
pkill -f w828_arm2.sh 2>/dev/null || true
for a in ta tc; do rm -f /home/albus/strata166/data/w828_ab2_$a.txt; done
setsid nohup bash /home/albus/strata166/tmp/w828_ab2.sh ta tc tc ta > /home/albus/strata166/data/w828_ab3.log 2>&1 < /dev/null &
sleep 20
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -8 /home/albus/strata166/data/w828_ab3.log
