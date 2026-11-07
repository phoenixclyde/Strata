# -*- coding: utf-8 -*-
"""166：抓引擎自带的预填分解（prefill ... chunks ... PLE ... ms）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 历史日志里所有 prefill 分解行 ==="
docker exec strata166 bash -lc 'grep -nE "prefill .* tokens in .* chunks" /data/*.log | tail -20'
echo "(空 = 该行只在 generate 模式或 --stats 下才打)"
echo
echo "=== 引擎 --help 里 stats / 分解相关 ==="
docker exec strata166 bash -lc '/src/build-906/strata --help 2>&1 | grep -inE "stats|chunks|ms_ple|breakdown|prefill " | head -20'
echo
echo "=== PrefillStats 字段是否在 serve 模式也会打：查全部含 chunks 的行 ==="
docker exec strata166 bash -lc 'grep -ncE "chunks" /data/strata-ud-q4_k_xl.log; grep -E "chunks" /data/strata-ud-q4_k_xl.log | tail -3'
echo
echo "=== 当前是否还在跑 / 配置 ==="
docker exec strata166 bash -lc 'ps -eo pid,etimes,args | grep -E "serve/[s]erver.py" | head -2; echo; python3 -c "
import json;a=json.load(open(\"/data/strata-ud-q4_k_xl.json\"))[\"args\"];print(\" \".join(map(str,a)))"'
docker exec strata166 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---'); print(e[:500])
