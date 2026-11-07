# -*- coding: utf-8 -*-
"""诊断：两个 strata 容器的状态与 docker start 的真实报错。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
set +e
echo "=== docker ps -a（strata 相关）==="
docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -i strata
echo
echo "=== 显式 docker start strata166-401（把报错打出来）==="
docker start strata166-401
echo "  start rc=$?"
sleep 4
docker ps -a --format '{{.Names}}|{{.Status}}' | grep strata166-401
echo
echo "=== 容器细节 ==="
docker inspect -f 'Running={{.State.Running}} ExitCode={{.State.ExitCode}} Error={{.State.Error}} StartedAt={{.State.StartedAt}}' strata166-401 2>&1
echo
echo "=== 8090 是否有监听 ==="
(docker exec strata166-401 bash -lc 'ps -eo pid,args | grep "[s]erver.py" || echo "(容器内无 server.py)"; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8090/v1/models') 2>&1 | tail -4
echo
echo "=== /data 现状 ==="
docker exec strata166-401 bash -lc 'ls -l /data/*.json 2>&1; echo "--- serve-run.log 尾 8 ---"; tail -8 /data/serve-run.log 2>&1' 2>&1
echo
echo "=== weights 现状 ==="
ls -l /home/albus/strata166/weights/
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=600)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:500])
