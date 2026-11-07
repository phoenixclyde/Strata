date +%H:%M:%S
echo "=== ta arm log tail ==="
tail -14 /home/albus/strata166/data/w828_ab2_ta.txt 2>/dev/null | cut -c1-180
echo "=== container ==="
docker ps --format '{{.Names}} {{.Status}}' | grep w828 || echo none
echo "=== engine log tail ==="
docker logs w828ta 2>&1 | tail -6 | cut -c1-170
echo "=== health ==="
curl -s --max-time 3 http://127.0.0.1:8090/health | head -c 100
echo
echo "=== last timing lines ==="
grep -ac "strata decode timing" /home/albus/strata166/data/w828_ta.log
tail -2 /home/albus/strata166/data/w828_ta.log | cut -c1-120
