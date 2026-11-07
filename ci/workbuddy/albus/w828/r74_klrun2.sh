cd /home/albus/strata166/tmp
pkill -f w828_arm4.sh 2>/dev/null || true
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker run --rm -v /home/albus/strata166/data:/data strata-gfx906:0.2.8 rm -f /data/w828kl/E0.tsv /data/w828kl/E0b.tsv /data/w828kl/Eall.tsv
ls -la /home/albus/strata166/data/w828kl/ 2>/dev/null
setsid nohup bash -c '
bash /home/albus/strata166/tmp/w828_arm4.sh e0   /data/w828_kle0.json   w828e0   /data/w828kl/E0.tsv   900
bash /home/albus/strata166/tmp/w828_arm4.sh e0b  /data/w828_kle0b.json  w828e0b  /data/w828kl/E0b.tsv  900
bash /home/albus/strata166/tmp/w828_arm4.sh eall /data/w828_kleall.json w828eall /data/w828kl/Eall.tsv 900
' > /home/albus/strata166/data/w828_kl2.log 2>&1 < /dev/null &
sleep 25
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -6 /home/albus/strata166/data/w828_kl2.log
