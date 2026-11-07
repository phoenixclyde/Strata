# -*- coding: utf-8 -*-
"""166：A/B 进行中的只读快照（当前 arm 的 env + 已完成的预填读数）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 当前在跑的 arm（进程 env）==="
docker exec strata166 bash -lc 'for p in $(pgrep -f "build-906/[s]trata"); do echo "engine pid=$p"; tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_(KQ256|PREFILL_MMQ|IQ_MT_MIN|NO_IQ4NL)" || echo "  (无 MMQ/KQ 相关 override => baseline)"; done'
echo
echo "=== server 启动时刻 / 已运行时长 ==="
docker exec strata166 bash -lc 'ps -eo pid,etimes,args | grep -E "serve/[s]erver.py" | head -2'
echo
echo "=== 引擎日志里全部 21589-token 预填读数（按时间顺序，每 arm 一条）==="
docker exec strata166 bash -lc 'grep -nE "prompt 21589 tokens" /data/strata-ud-q4_k_xl.log | tail -8'
echo
echo "=== 最近 5 条 prompt 读数（含短 prompt）==="
docker exec strata166 bash -lc 'grep -E "prompt [0-9]+ tokens =" /data/strata-ud-q4_k_xl.log | tail -5'
echo
echo "=== serve-run.log 尾 4（看当前 arm 是否已 ready）==="
docker exec strata166 bash -lc 'tail -4 /data/serve-run.log'
echo
echo "=== 8090 ==="
docker exec strata166 bash -lc 'curl -s -m 10 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---'); print(e[:500])
