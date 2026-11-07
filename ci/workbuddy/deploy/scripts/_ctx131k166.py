# -*- coding: utf-8 -*-
"""166：把 max-context 从 8192 提到 131072 并重启验证"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 0) 备份当前 8k 配置 ==="
docker exec strata166 bash -lc 'cp -n /data/strata-ud-q4_k_xl.json /data/strata-ud-q4_k_xl-8k.json.bak; ls -l /data/*.json*'
echo
echo "=== 1) 改 --max-context 8192 -> 131072 ==="
docker exec -i strata166 python3 - <<'PYEOF'
import json, pathlib
p = pathlib.Path('/data/strata-ud-q4_k_xl.json')
cfg = json.loads(p.read_text())
a = cfg['args']
i = a.index('--max-context')
print('before:', a[i], a[i+1])
a[i+1] = '131072'
p.write_text(json.dumps(cfg, indent=1))
cfg2 = json.loads(p.read_text())
a2 = cfg2['args']
print('after :', a2[a2.index('--max-context')], a2[a2.index('--max-context')+1])
print('full args:', ' '.join(str(x) for x in a2))
PYEOF
echo "rc=$?"
echo
echo "=== 2) 重启（带 131072 上下文）==="
docker exec strata166 bash -lc 'pkill -f "build-906/strata"; pkill -f "serve/server.py"; sleep 3; echo cleaned'
docker exec strata166 bash -lc 'cd /src && setsid nohup python3 serve/server.py --engine strata --config /data/strata-ud-q4_k_xl.json --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started'
sleep 8
for i in $(seq 1 22); do
  sleep 30
  echo "===== T+$((i*30))s ====="
  docker exec strata166 bash -lc 'tail -3 /data/serve-run.log; echo "[engine]"; tail -4 /data/strata-ud-q4_k_xl.log; echo "[mem]"; free -g | head -2'
  if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log 2>/dev/null'; then
    echo "### READY ###"; break
  fi
  if ! docker exec strata166 bash -lc 'ps aux | grep -q "[s]erve/server.py"'; then
    echo "### SERVER 已退出 ###"; break
  fi
done
echo
echo "=== 3) 就绪后：VRAM / 关键行 ==="
docker exec strata166 bash -lc 'rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total"'
docker exec strata166 bash -lc 'grep -E "prompt chunk|borrows|VRAM free|expert cache|max_context|context" /data/strata-ud-q4_k_xl.log | tail -10'
docker exec strata166 bash -lc 'curl -s -m 15 http://127.0.0.1:8090/v1/models'
echo
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('--- STDERR ---')
    print(r.stderr.decode('utf-8', 'replace')[:800])
