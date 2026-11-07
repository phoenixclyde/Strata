L=/home/albus/strata166/src028/build-028w.log
date +%H:%M:%S
grep -oE '^\[[0-9]+/[0-9]+\]' $L | tail -1
grep -c 'Building' $L || true
docker ps --format '{{.Names}}' | grep buildrun || echo "build container gone"
grep -aE 'error:' $L | head -5
curl -s --max-time 3 http://127.0.0.1:8090/health | head -c 60
