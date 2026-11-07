# -*- coding: utf-8 -*-
"""166：只读检查 MMQ 回退日志（两个日志都翻）+ 当前进程 env"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 全容器日志里搜 MMQ 回退提示（#420）==="
docker exec strata166 bash -lc 'grep -rniE "prompt kernels|non-MMQ|no tile|mmq" /data/*.log 2>/dev/null | head -20; echo "(以上为空=没有回退提示)"; echo'
echo "=== serve-run.log 尾部 ==="
docker exec strata166 bash -lc 'tail -5 /data/serve-run.log'
echo
echo "=== 当前 server 进程与它继承的 STRATA_* env ==="
docker exec strata166 bash -lc 'for p in $(pgrep -f "serve/[s]erver.py"); do echo "pid=$p"; tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_" ; done'
echo
echo "=== 当前 engine 进程 env 里的 STRATA_* ==="
docker exec strata166 bash -lc 'for p in $(pgrep -f "build-906/[s]trata"); do echo "pid=$p"; tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_"; done'
echo
echo "=== server.py 是怎么开日志的（stdout/stderr 会不会进 log）==="
docker exec strata166 bash -lc 'grep -nE "stderr|stdout|open\(.*log|Popen" /src/serve/server.py | head -20'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---'); print(e[:600])
