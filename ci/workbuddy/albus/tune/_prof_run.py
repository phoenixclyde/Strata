# -*- coding: utf-8 -*-
"""用 rocprofv3 在临时容器里 profile 一个 S 档请求，然后把生产起回来。
安全设计：生产先停 -> 临时容器用 8091 端口 -> 无论成败，finally 都恢复生产。
"""
import base64, subprocess, sys, time

HOST = "albus@192.168.50.166"

def run(script, timeout=600):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(script.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace")

PROF = r'''
set -u
PROD=strata166-407
PROFC=strata-prof
IMG=strata-gfx906:0.2.4
OUT=/home/albus/strata166/data/_prof
rm -rf $OUT && mkdir -p $OUT

echo "=== 1 stop prod ==="
docker stop $PROD >/dev/null 2>&1; echo rc=$?

echo "=== 2 run profiled engine on 8091 ==="
docker rm -f $PROFC >/dev/null 2>&1
docker run -d --name $PROFC \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --ulimit memlock=-1 --shm-size=64m \
  --security-opt label=disable \
  -p 8091:8091 \
  -v /home/albus/strata166/data:/data \
  -v /models:/models:ro \
  --entrypoint bash $IMG -lc 'cd /src && exec /opt/rocm/bin/rocprofv3 --kernel-trace --stats -o /data/_prof/run -- python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8091' >/dev/null 2>&1
echo "run rc=$?"

echo "=== 3 wait ready (max 150s) ==="
ok=0
for i in $(seq 1 150); do
  if curl -s --max-time 2 http://127.0.0.1:8091/health >/dev/null 2>&1; then echo "ready after ${i}s"; ok=1; break; fi
  sleep 1
done
if [ $ok = 0 ]; then echo "NOT READY"; docker logs --tail 20 $PROFC 2>&1; fi
'''

FIRE = r'''
set -u
python3 - <<'PY'
import json, urllib.request, time
body={"model":"qwen3.8-flash-next-ud-iq4_xs-abliterated",
      "messages":[{"role":"user","content":"预热"}],"max_tokens":8,"temperature":0}
def post(u,b):
    r=urllib.request.Request(u,data=json.dumps(b).encode(),headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r,timeout=300).read().decode())
base="http://127.0.0.1:8091/v1/chat/completions"
try:
    post(base,body)
    print("warmup ok")
except Exception as e:
    print("warmup ERR",e)
PY
echo "=== 5 profiled request ==="
python3 /home/albus/strata166/tmp/w776_bench.py S 1 2>&1 | tail -2
sleep 4
'''

DONE = r'''
set -u
PROD=strata166-407
PROFC=strata-prof
echo "=== 6 stop prof container ==="
docker stop $PROFC >/dev/null 2>&1; echo rc=$?
sleep 2
echo "=== 7 outputs ==="
ls -l /home/albus/strata166/data/_prof/ 2>/dev/null | head -8
echo "=== 8 restore prod ==="
docker start $PROD >/dev/null 2>&1; echo rc=$?
for i in $(seq 1 90); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then echo "prod ready after ${i}s"; break; fi
  sleep 1
done
docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}' | grep strata166 | head -2
'''

if __name__ == "__main__":
    rc, o = run(PROF, 900)
    print(o[-2500:])
    if "ready after" in o:
        rc2, o2 = run(FIRE, 900)
        print(o2[-1500:])
    rc3, o3 = run(DONE, 900)
    print(o3[-1800:])
