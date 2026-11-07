import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
pkill -9 -f ab_p4.sh; sleep 2; pkill -9 -f w776_bench; sleep 1
echo "=== containers before ==="
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166-407 | head -4
'''))
print(sh(r'''
# 旧容器（p3）还在跑并占着 8090 —— 先停掉并删除；新容器（p4）若因端口冲突已退出则删掉重建
docker stop -t 20 strata166-407.bak_w794 >/dev/null 2>&1; docker rm -f strata166-407.bak_w794 >/dev/null 2>&1
docker rm -f strata166-407 >/dev/null 2>&1
docker run -d --name strata166-407 \
  --device /dev/kfd --device /dev/dri \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  -p 8090:8090 --network bridge --ipc host --group-add video \
  --restart unless-stopped \
  strata-gfx906:0.2.4p4 /bin/bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >/dev/null 2>&1
sleep 3; docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166 | head -2
for i in $(seq 1 200); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "p4 ready ${i}s"; break; }; sleep 1; done
''', t=300))
