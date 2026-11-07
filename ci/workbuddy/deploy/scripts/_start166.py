# -*- coding: utf-8 -*-
"""166：容器内启动 Strata serve（首启 ctx 8192），并轮询到 ready 或报错。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 启动 serve（detached）==="
docker exec -d strata166 bash -lc 'cd /src && setsid nohup python3 serve/server.py --engine strata --config /data/strata-ud-q4_k_xl.json --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started'
sleep 5
echo "--- 容器内进程 ---"
docker exec strata166 bash -lc 'ps aux | grep -E "server.py|strata" | grep -v grep | head -5'
echo
for i in $(seq 1 16); do
  sleep 30
  echo "===== T+$((i*30))s ====="
  docker exec strata166 bash -lc 'echo "--- serve-run.log 尾 8 ---"; tail -8 /data/serve-run.log 2>&1; echo "--- engine log 尾 12 ---"; tail -12 /data/strata-ud-q4_k_xl.log 2>&1; echo "--- 进程 ---"; ps aux | grep -E "server.py|build-906/strata" | grep -v grep | awk "{print \$3, \$4, \$11, \$12}" | head -4; free -g | head -2'
  if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log /data/strata-ud-q4_k_xl.log 2>/dev/null'; then
    echo "### READY ###"; break
  fi
  if ! docker exec strata166 bash -lc 'ps aux | grep -q "[s]erver.py"'; then
    echo "### SERVER 进程已退出 ###"; break
  fi
done
echo
echo "=== 最终状态 ==="
docker exec strata166 bash -lc 'echo "--- serve-run.log 全 30 ---"; tail -30 /data/serve-run.log; echo "--- engine log 全 25 ---"; tail -25 /data/strata-ud-q4_k_xl.log'
docker exec strata166 bash -lc 'curl -s -m 10 -o /dev/null -w "8090 http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:800])
