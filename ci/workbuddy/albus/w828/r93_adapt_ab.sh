cd /home/albus/strata166/tmp
pkill -f w828_ab2.sh 2>/dev/null || true
setsid nohup bash /home/albus/strata166/tmp/w828_ab2.sh ta tm tm ta > /home/albus/strata166/data/w828_adapt_ab.log 2>&1 < /dev/null &
sleep 18
date +%H:%M:%S
head -4 /home/albus/strata166/data/w828_adapt_ab.log
