R=""
for i in $(seq 1 420); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then R=$i; break; fi
  sleep 1
done
date +%H:%M:%S
echo "READY_AT=$R"
if [ -z "$R" ]; then echo "NOT READY"; docker logs w828b154n 2>&1 | tail -8 | cut -c1-170; exit 4; fi
docker logs w828b154n > /data/w828_arm_b154n.log 2>&1
echo "--- startup lines ---"
grep -a -E "engine started|expert cache auto|expert arena|native pack|0\.1\.54|slots" /data/w828_arm_b154n.log | head -8 | cut -c1-180
