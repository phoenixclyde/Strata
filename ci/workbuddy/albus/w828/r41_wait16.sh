R=""
for i in $(seq 1 480); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then R=$i; break; fi
  sleep 1
done
date +%H:%M:%S
echo "READY=$R"
if [ -z "$R" ]; then docker logs w828w16 2>&1 | tail -12 | cut -c1-180; exit 4; fi
docker logs w828w16 2>&1 > /home/albus/strata166/tmp/w828w16.log
grep -a -E "batch|slots|window|filling the GPU" /home/albus/strata166/tmp/w828w16.log | head -12 | cut -c1-180
