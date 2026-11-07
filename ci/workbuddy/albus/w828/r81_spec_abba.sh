cd /home/albus/strata166/tmp
pkill -f w828_ab2.sh 2>/dev/null || true
rm -f /home/albus/strata166/data/w828_ab2_*.txt
rm -f /home/albus/strata166/data/w828_trace/spec_*.txt
setsid nohup bash /home/albus/strata166/tmp/w828_ab2.sh ta tf tg th > /home/albus/strata166/data/w828_spec_ab.log 2>&1 < /dev/null &
sleep 25
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -8 /home/albus/strata166/data/w828_spec_ab.log
