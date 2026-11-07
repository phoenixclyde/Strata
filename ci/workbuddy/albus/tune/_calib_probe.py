import subprocess, base64

HOST = "albus@192.168.50.166"

SH = r'''
set -u
cd /home/albus/strata166
cat > calib_run.sh <<'EOF'
#!/bin/sh
set -u
cd /home/albus/strata166
echo "[$(date '+%F %T')] === stop production ==="
docker stop strata166-407 >/dev/null 2>&1
echo "[$(date '+%F %T')] === run calibrate ==="
docker run --rm --name strata-calib \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --ulimit memlock=-1 --shm-size=64m \
  --security-opt label=disable \
  -v /home/albus/strata166/data:/data \
  -v /models:/models:ro \
  -w /src \
  strata-gfx906:0.2.4 \
  python3 tools/calibrate.py /data/strata-huihui-ud-iq4_xs.json \
  > /home/albus/strata166/data/calib.out 2>&1
RC=$?
echo "[$(date '+%F %T')] === calibrate rc=$RC ===" >> /home/albus/strata166/data/calib.out
echo "[$(date '+%F %T')] === restore production ==="
docker start strata166-407 >/dev/null 2>&1
echo "[$(date '+%F %T')] === done ===" >> /home/albus/strata166/data/calib.out
EOF
chmod +x calib_run.sh
rm -f data/calib.out
nohup ./calib_run.sh > data/calib.driver.log 2>&1 &
echo "launched pid=$!"
sleep 100
echo "=== driver log ==="
cat data/calib.driver.log 2>/dev/null | tail -5
echo "=== calib.out (first 40) ==="
head -40 data/calib.out 2>/dev/null
echo "=== container ==="
docker ps -a --format '{{.Names}}|{{.Status}}' | grep -E 'strata-calib|strata166-407'
'''

p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", HOST, "base64 -d | bash"],
                   input=base64.b64encode(SH.encode()).decode("ascii").encode("ascii"),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=400)
print(p.stdout.decode("utf-8", "replace"))
