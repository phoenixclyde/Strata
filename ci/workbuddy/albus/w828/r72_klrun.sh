cd /home/albus/strata166/tmp
pkill -f w828_arm4.sh 2>/dev/null || true
setsid nohup bash -c '
bash /home/albus/strata166/tmp/w828_arm4.sh e0    /data/w828_kle0.json  w828e0    /data/w828kl/E0.tsv
bash /home/albus/strata166/tmp/w828_arm4.sh e0b   /data/w828_kle0b.json w828e0b   /data/w828kl/E0b.tsv
bash /home/albus/strata166/tmp/w828_arm4.sh eall  /data/w828_kleall.json w828eall /data/w828kl/Eall.tsv
' > /home/albus/strata166/data/w828_kl.log 2>&1 < /dev/null &
sleep 20
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -6 /home/albus/strata166/data/w828_kl.log
