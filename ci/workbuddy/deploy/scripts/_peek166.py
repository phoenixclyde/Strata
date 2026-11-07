# -*- coding: utf-8 -*-
"""直探 166：131072 上下文有没有起来"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 进程 ==="
docker exec strata166 bash -lc 'ps aux | grep -E "server.py|build-906/strata" | grep -v grep | awk "{print \$3, \$4, \$11, \$12, \$13, \$14}" | head -4'
echo
echo "=== 当前配置 ==="
docker exec strata166 bash -lc 'python3 -c "import json;a=json.load(open(\"/data/strata-ud-q4_k_xl.json\"))[\"args\"];i=a.index(\"--max-context\");print(a[i],a[i+1]);print(\" \".join(map(str,a)))"'
echo
echo "=== serve-run.log 尾 8 ==="
docker exec strata166 bash -lc 'tail -8 /data/serve-run.log 2>&1'
echo
echo "=== engine log 尾 14 ==="
docker exec strata166 bash -lc 'tail -14 /data/strata-ud-q4_k_xl.log 2>&1'
echo
echo "=== 引擎日志大小/时间 ==="
docker exec strata166 bash -lc 'ls -l --time-style=+%H:%M:%S /data/strata-ud-q4_k_xl.log'
echo
echo "=== VRAM ==="
docker exec strata166 bash -lc 'rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total"'
echo
echo "=== mem ==="
docker exec strata166 bash -lc 'free -g | head -2'
echo
echo "=== 8090 ==="
docker exec strata166 bash -lc 'curl -s -m 10 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
echo
echo "=== 宿主负载 ==="
uptime; echo; date
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=180)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---')
    print(e[:600])
