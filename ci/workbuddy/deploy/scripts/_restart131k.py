# -*- coding: utf-8 -*-
"""166：自免式清理（pkill 模式不会匹配自身）+ 用 131072 配置重启 + 轮询 ready"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 0) 自免式清理（[s] 技巧避免 pkill 杀到自己）==="
docker exec strata166 bash -lc 'pkill -9 -f "build-906/[s]trata"; pkill -9 -f "serve/[s]erver.py"; sleep 3; echo "-- 残留进程 --"; ps aux | grep -E "server\.py|build-906/strata" | grep -v grep | head -4; echo "(以上为空即干净)"'
echo
echo "=== 1) 8090 是否还被占 ==="
docker exec strata166 bash -lc 'ss -ltnp 2>/dev/null | grep 8090 || echo "8090 空闲"'
echo
echo "=== 2) 启动（131072 上下文）==="
docker exec strata166 bash -lc 'cd /src && setsid nohup python3 serve/server.py --engine strata --config /data/strata-ud-q4_k_xl.json --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started'
sleep 10
docker exec strata166 bash -lc 'head -3 /data/serve-run.log; echo "-- 进程 --"; ps aux | grep -E "server\.py|build-906/strata" | grep -v grep | awk "{print \$3, \$4, \$11, \$12}" | head -4'
echo
for i in $(seq 1 24); do
  sleep 30
  echo "===== T+$((i*30))s ====="
  docker exec strata166 bash -lc 'tail -2 /data/serve-run.log; echo "[engine]"; tail -3 /data/strata-ud-q4_k_xl.log'
  if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log 2>/dev/null'; then
    echo "### READY ###"; break
  fi
  if ! docker exec strata166 bash -lc 'ps aux | grep -q "[s]erve/server.py"'; then
    echo "### SERVER 已退出 ###"; break
  fi
done
echo
echo "=== 3) 最终 ==="
docker exec strata166 bash -lc 'tail -12 /data/serve-run.log'
docker exec strata166 bash -lc 'grep -E "prompt chunk|borrows|VRAM free|expert cache [0-9]|resident RAM mode|mtp:" /data/strata-ud-q4_k_xl.log | tail -10'
docker exec strata166 bash -lc 'rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total"'
docker exec strata166 bash -lc 'curl -s -m 15 http://127.0.0.1:8090/v1/models; echo'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
with open(r'D:\strata166\logs\_restart131k.txt', 'w', encoding='utf-8') as f:
    f.write(r.stdout.decode('utf-8', 'replace'))
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:800])
print('done')
