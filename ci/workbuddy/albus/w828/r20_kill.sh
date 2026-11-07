pkill -f w828_ab.sh 2>/dev/null || true
pkill -f w828_arm.sh 2>/dev/null || true
sleep 2
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep w828 || echo "no arm container"
echo "--- b154n log tail ---"
docker logs w828b154n 2>&1 | tail -4 | cut -c1-160
echo "--- ready? ---"
curl -s --max-time 3 http://127.0.0.1:8090/health | head -c 120
echo
echo "--- config still intact? ---"
python3 -c "import json;c=json.load(open('/home/albus/strata166/data/w828_b154n.json'));print(c['exe'], len(c['args']))"
