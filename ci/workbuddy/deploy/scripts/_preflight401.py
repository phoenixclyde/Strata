# -*- coding: utf-8 -*-
"""预飞：用现有 /data（0.1.39 出的 pack）启动 0.1.40.1 引擎，确认能 ready 并出真读数。"""
import base64, os, subprocess, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
                        '-i', KEY, HOST, 'base64 -d | bash'], input=b.encode('ascii'),
                       capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


print('[1] 停掉占用 8090 的 strata 容器')
o, e = ssh(r'''
set +e
for n in strata166 strata166-401; do
  if docker ps -a --format '{{.Names}}' | grep -qx "$n"; then docker stop -t 20 "$n" >/dev/null 2>&1; echo "stopped $n"; fi
done
sleep 3
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata || echo "(无 strata 容器在跑)"
echo "--- 8090 监听检查 ---"
(docker exec strata166 bash -lc 'ps -eo pid,args | grep "[s]erver.py" || echo "(容器内无 server.py)"') 2>/dev/null || echo "(容器未运行)"
''', 300)
print(o.strip())

print()
print('[2] 建/起 0.1.40.1 容器（与 0.1.39 完全相同的挂载与设备）')
o, e = ssh(r'''
set -e
if ! docker ps -a --format '{{.Names}}' | grep -qx strata166-401; then
  docker run -d --name strata166-401 \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    --ipc=host --ulimit memlock=-1 \
    -v /home/albus/strata166/weights:/weights:ro \
    -v /home/albus/strata166/data:/data \
    -p 8090:8090 \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    --restart no \
    strata-gfx906:0.1.40.1 sleep infinity
  echo "created"
else
  docker start strata166-401 >/dev/null 2>&1 || true
  echo "started(existing)"
fi
sleep 2
docker ps --format '{{.Names}}|{{Status}}' 2>/dev/null | grep strata166-401 || docker ps --format '{{.Names}}|{{.Status}}' | grep strata166-401
echo "--- 容器内 rocminfo 认卡 ---"
docker exec strata166-401 bash -lc 'rocminfo 2>/dev/null | grep -m1 -E "gfx[0-9]+" ; ls -l /work' 2>/dev/null || true
''', 600)
print(o.strip(), ('| ERR ' + e[:300]) if e.strip() else '')

print()
print('[3] 启动 serve（0.1.40.1），后台')
o, e = ssh('docker exec -d strata166-401 bash -lc \'cd /src && setsid nohup python3 serve/server.py '
           '--engine strata --config /data/strata-ud-q4_k_xl.json --port 8090 '
           '> /data/serve-run.log 2>&1 < /dev/null\'; echo launched', 300)
print(o.strip())

print()
print('[4] 轮询就绪（HTTP 探针；最多 12 分钟）')
ready = False
for i in range(36):
    time.sleep(20)
    o, _ = ssh('docker exec strata166-401 bash -lc \'curl -s -o /dev/null -w "%%{http_code}" '
               'http://127.0.0.1:8090/v1/models; echo; tail -1 /data/serve-run.log\'', 120)
    lines = o.strip().splitlines()
    code = (lines or [''])[0].strip()
    last = (lines or ['', ''])[-1]
    print('  [%3ds] http=%s  %s' % ((i + 1) * 20, code, last[:110]), flush=True)
    if code == '200':
        ready = True
        break

print()
print('[5] 结果')
if ready:
    o, _ = ssh(r'''docker exec strata166-401 bash -lc '
cat > /tmp/q.json <<JSON
{"model":"qwen3.8-flash-next-ud-q4_k_xl","messages":[{"role":"user","content":"Reply with exactly: FLY-401-OK"}],"max_tokens":24,"temperature":0}
JSON
echo "=== /v1/models ==="
curl -s http://127.0.0.1:8090/v1/models | head -c 400; echo
echo "=== 真问答 ==="
curl -s http://127.0.0.1:8090/v1/chat/completions -H "Content-Type: application/json" -d @/tmp/q.json | head -c 900; echo
' ''', 300)
    print(o)
    print('[6] 释放：停掉该容器（把 8090 还给对拍脚本）')
    o, _ = ssh('docker stop -t 20 strata166-401 >/dev/null 2>&1; echo stopped', 300)
    print(o.strip())
else:
    o, _ = ssh('docker exec strata166-401 bash -lc \'echo "=== serve-run.log 尾 30 ==="; tail -30 /data/serve-run.log; '
               'echo; echo "=== 引擎日志尾 20 ==="; tail -20 /data/strata-ud-q4_k_xl.log\'', 300)
    print(o[-3000:])
