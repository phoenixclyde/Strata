# -*- coding: utf-8 -*-
"""166：把引擎日志里所有解码读数抽出来取极值；顺带看第四轮进度"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 全部解码读数（按日志顺序）==="
docker exec strata166 bash -lc 'grep -oE "[0-9]+ generated in [0-9]+ ms \([0-9.]+ tok/s\)" /data/strata-ud-q4_k_xl.log'
echo
echo "=== 取极值 ==="
docker exec strata166 bash -lc 'grep -oE "[0-9]+ generated in [0-9]+ ms \([0-9.]+ tok/s\)" /data/strata-ud-q4_k_xl.log | awk -F"[()]" "{print \$2}" | sed "s/ tok\/s//" | sort -rn | head -5'
echo
echo "=== 引擎日志里与解码相关的其它行（并发/池/命中）==="
docker exec strata166 bash -lc 'grep -E "expert-pool workers|resident experts|prompt chunk|borrows" /data/strata-ud-q4_k_xl.log | tail -4'
echo
echo "=== 第四轮进度：当前配置 + 最新读数 ==="
docker exec strata166 bash -lc 'python3 -c "
import json
a=json.load(open(\"/data/strata-ud-q4_k_xl.json\"))[\"args\"]
print(\" \".join(map(str,a)))"'
docker exec strata166 bash -lc 'ps -eo pid,etimes,args | grep -E "serve/[s]erver.py" | head -2'
docker exec strata166 bash -lc 'grep -E "prompt 18074 tokens = 0 reused" /data/strata-ud-q4_k_xl.log | tail -6'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---'); print(e[:500])
