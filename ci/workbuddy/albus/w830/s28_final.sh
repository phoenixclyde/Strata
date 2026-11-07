date +%H:%M:%S
echo "--- container / image / exe ---"
docker ps --format '{{.Names}} {{.Status}} {{.Image}}' | grep strata166
python3 -c "
import json;c=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
print('exe:', c['exe'], '| args', len(c['args']), '| env', len(c['env']))"
echo "--- health + the restored telemetry series ---"
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 120; echo
curl -s --max-time 8 http://127.0.0.1:8090/metrics | grep -o 'gpu_pcie_rx_mb[^,}]*' | head -2
echo "--- patch gate (must be all OK) ---"
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -12
