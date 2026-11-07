echo "=== startup (first 80 lines) ==="
docker logs w828b154n 2>&1 | head -80 | grep -a -E "0\.1\.54|expert cache|expert arena|native pack|slots|VRAM|window" | cut -c1-190
echo "=== any cache line anywhere ==="
docker logs w828b154n 2>&1 | grep -a -E "expert cache auto" | cut -c1-200
echo "=== timing env? ==="
python3 -c "import json;c=json.load(open('/home/albus/strata166/data/w828_b154n.json'));print(sorted(c['env']))"
