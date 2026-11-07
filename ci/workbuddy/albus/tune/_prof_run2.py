# -*- coding: utf-8 -*-
"""用 rocprofv3 在临时容器里 profile 一个 decode 请求。
安全：try/finally 保证生产在任何路径下都被起回来（上次停 21 小时的教训）。
"""
import base64, subprocess, sys

HOST = "albus@192.168.50.166"

def run(script, timeout=900):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(script.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")

STOP = r'''
docker stop strata166-407 >/dev/null 2>&1; echo "prod stopped rc=$?"
docker rm -f strata-prof >/dev/null 2>&1
rm -rf /home/albus/strata166/data/_prof && mkdir -p /home/albus/strata166/data/_prof
docker run -d --name strata-prof \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --ulimit memlock=-1 --shm-size=64m \
  --security-opt label=disable -p 8091:8091 \
  -v /home/albus/strata166/data:/data -v /models:/models:ro \
  --entrypoint bash strata-gfx906:0.2.4 -lc \
  'cd /src && exec /opt/rocm/bin/rocprofv3 --kernel-trace --stats -o /data/_prof/run -- python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8091' >/dev/null 2>&1
echo "prof container rc=$?"
for i in $(seq 1 150); do
  if curl -s --max-time 2 http://127.0.0.1:8091/health >/dev/null 2>&1; then echo "READY ${i}s"; sleep 20; echo "settled"; break; fi
  sleep 1
done
'''

FIRE = r'''
python3 /home/albus/strata166/tmp/_prof_fire.py 2>&1 | tail -4
sleep 4
'''

DONE = r'''
echo "=== stop prof ==="
docker stop strata-prof >/dev/null 2>&1; echo "rc=$?"
sleep 2
docker rm -f strata-prof >/dev/null 2>&1
echo "=== outputs ==="
ls -l /home/albus/strata166/data/_prof/ 2>/dev/null | head -8
echo "=== RESTORE PROD ==="
docker start strata166-407 >/dev/null 2>&1; echo "start rc=$?"
for i in $(seq 1 120); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then echo "PROD READY ${i}s"; break; fi
  sleep 1
done
docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}' | grep strata166 | head -2
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('ver',e['version'],'slots',e['expert_slots'])" 2>/dev/null
'''

if __name__ == "__main__":
    try:
        print(run(STOP)[-1200:])
        print(run(FIRE)[-800:])
    finally:
        print(run(DONE)[-1600:])
