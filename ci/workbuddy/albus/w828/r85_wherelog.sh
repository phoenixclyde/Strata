date +%H:%M:%S
C=$(docker ps --format '{{.Names}}' | grep w828 | head -1)
echo "container=$C"
echo "--- docker logs: any timing/depth/trace line? ---"
docker logs "$C" 2>&1 | grep -aE "decode timing|spec depth|mTP|MTP" | tail -6 | cut -c1-160
echo "--- docker logs tail (last 12 lines) ---"
docker logs "$C" 2>&1 | tail -12 | cut -c1-170
echo "--- engine stderr redirection in server.py ---"
grep -n "stderr\|STDOUT\|log_file\|logpath\|\.log\b" /home/albus/strata166/src028/serve/server.py | head -25
echo "--- recently written files in container ---"
docker exec "$C" bash -lc "ls -lat /tmp /data 2>/dev/null | head -20"
