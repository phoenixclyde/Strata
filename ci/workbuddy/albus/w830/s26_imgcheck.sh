C=w830tn
echo "=== does the running (new) image carry the web-UI patch too? ==="
docker exec $C bash -lc 'grep -c -F saveApiKey /src/serve/web/app.js; grep -c -F tab-btn-images /src/serve/web/app.js'
echo "=== and the telemetry patch? ==="
docker exec $C bash -lc 'grep -c -F BW_REFRESH_S /src/serve/telemetry.py'
echo "=== HTTP root + metrics while an arm is up ==="
curl -s -o /dev/null -w '  / -> %{http_code}\n' --max-time 6 http://127.0.0.1:8090/
curl -s --max-time 6 http://127.0.0.1:8090/metrics | grep -o 'gpu_pcie_rx_mb[^,}]*' | head -2
