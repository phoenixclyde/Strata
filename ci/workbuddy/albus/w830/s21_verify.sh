cd /home/albus/strata166/tmp
echo "=== 1. TTFT (same harness: 3 warm-ups, 1151/2213/4345 x2) ==="
timeout 900 python3 w828_ttft3.py 8090 1200,2400,4800 2 3 2>&1 | tail -12
echo
echo "=== 2. decode (3 x 512 greedy) ==="
timeout 400 python3 mt_gen.py 8090 w830n2 /tmp/w830n2.json dec_corpus.json 512 3 2>&1 | grep -aE "p[0-9] |MEDIAN" | tail -5
echo
echo "=== 3. telemetry: is our AMD PCIe bandwidth back? ==="
for ep in /metrics /telemetry /api/monitor; do
  code=$(curl -s -o /tmp/tel.out -w '%{http_code}' --max-time 6 "http://127.0.0.1:8090$ep")
  echo "  $ep -> $code  $(head -c 90 /tmp/tel.out | tr -d '\n')"
  grep -o "gpu_pcie_rx_mb[^,}]*" /tmp/tel.out | head -2
done
