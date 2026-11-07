# -*- coding: utf-8 -*-
"""直查 166 上 IQ4_XS 服务的启动状态（引号全部用单引号，避免嵌套转义踩坑）。"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
set +e
echo "now $(date +%H:%M:%S)"
echo "=== 容器 ==="
docker ps -a --format '{{.Names}}|{{.Status}}' | grep -i strata
echo
echo "=== 容器内相关进程 ==="
docker exec strata166-401 bash -lc "ps -eo pid,etime,args | grep -E '[s]erver\.py|[s]trata' | head -6"
echo
echo "=== serve-run.log 尾 5 ==="
docker exec strata166-401 bash -lc 'tail -5 /data/serve-run.log'
echo
echo "=== 引擎日志尾 10 ==="
docker exec strata166-401 bash -lc 'tail -10 /data/strata-ud-iq4_xs.log 2>&1'
echo
echo "=== HTTP ==="
docker exec strata166-401 bash -lc 'curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8090/v1/models'
echo "=== 显存 ==="
rocm-smi --showmemuse 2>/dev/null | grep -i vram | head -2
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:300])
