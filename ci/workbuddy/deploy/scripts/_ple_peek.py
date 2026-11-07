# -*- coding: utf-8 -*-
"""166：PLE A/B 进行中的只读快照"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 当前配置里的 ple 相关参数 ==="
docker exec strata166 bash -lc 'python3 -c "
import json
a=json.load(open(\"/data/strata-ud-q4_k_xl.json\"))[\"args\"]
print(\" \".join(str(x) for x in a))
"'
echo
echo "=== 最近 6 条 prompt 读数（每条 = 一个 arm）==="
docker exec strata166 bash -lc 'grep -E "prompt [0-9]+ tokens =" /data/strata-ud-q4_k_xl.log | tail -6'
echo
echo "=== 引擎日志里 PLE 相关行 ==="
docker exec strata166 bash -lc 'grep -iE "ple" /data/strata-ud-q4_k_xl.log | tail -5'
echo
echo "=== 当前进程 / 内存 ==="
docker exec strata166 bash -lc 'ps -eo pid,etimes,args | grep -E "serve/[s]erver.py" | head -2; echo; free -g | head -3'
echo
echo "=== serve-run.log 尾 3 + 8090 ==="
docker exec strata166 bash -lc 'tail -3 /data/serve-run.log; curl -s -m 10 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---'); print(e[:500])
