# -*- coding: utf-8 -*-
"""166：轮询 131072 实例到 ready"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
for i in $(seq 1 22); do
  sleep 30
  echo "===== T+$((i*30))s ====="
  docker exec strata166 bash -lc 'tail -2 /data/serve-run.log; echo "[engine]"; tail -3 /data/strata-ud-q4_k_xl.log'
  if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log 2>/dev/null'; then
    echo "### READY ###"; break
  fi
  if ! docker exec strata166 bash -lc 'ps -eo args | grep -q "[s]erve/server.py"'; then
    echo "### SERVER 已退出 ###"; break
  fi
done
echo
echo "=== 最终 ==="
docker exec strata166 bash -lc 'tail -10 /data/serve-run.log'
echo "--- 引擎关键行 ---"
docker exec strata166 bash -lc 'grep -E "prompt chunk|borrows|VRAM free|expert cache [0-9]|resident RAM mode|mtp:|max_context" /data/strata-ud-q4_k_xl.log | tail -10'
echo "--- VRAM ---"
docker exec strata166 bash -lc 'rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total"'
echo "--- models ---"
docker exec strata166 bash -lc 'curl -s -m 15 http://127.0.0.1:8090/v1/models; echo'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
with open(r'D:\strata166\logs\_ready131k.txt', 'w', encoding='utf-8') as f:
    f.write(r.stdout.decode('utf-8', 'replace'))
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:600])
print('done -> D:\\strata166\\logs\\_ready131k.txt')
