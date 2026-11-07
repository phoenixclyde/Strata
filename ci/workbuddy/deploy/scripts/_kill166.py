# -*- coding: utf-8 -*-
"""166：精确按 PID 清掉占 8090 的进程，再启动"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== A) 容器内所有相关进程（含 PID 与完整 cmdline）==="
docker exec strata166 bash -lc 'ps -eo pid,ppid,etime,pcpu,args | grep -E "server\.py|build-906|strata" | grep -v grep'
echo
echo "=== B) 谁占着 8090（容器内）==="
docker exec strata166 bash -lc 'ss -ltnp 2>/dev/null | grep -E ":8090|LISTEN" | head -10 ; echo "--- pkill 是否存在 ---"; which pkill pgrep ss fuser 2>&1'
echo
echo "=== C) 宿主上谁占 8090 ==="
ss -ltnp 2>/dev/null | grep 8090 || echo "(宿主 8090 无监听)"
echo
echo "=== D) 精确 kill ==="
docker exec strata166 bash -lc 'for p in $(ps -eo pid,args | grep -E "server\.py|build-906/strata" | grep -v grep | awk "{print \$1}"); do echo "kill $p"; kill -9 $p 2>&1; done; sleep 3'
echo "--- kill 后 ---"
docker exec strata166 bash -lc 'ps -eo pid,args | grep -E "server\.py|build-906/strata" | grep -v grep || echo "(无残留)"'
docker exec strata166 bash -lc 'ss -ltnp 2>/dev/null | grep 8090 || echo "8090 已空闲(容器内)"'
echo
echo "=== E) 启动 ==="
docker exec strata166 bash -lc 'cd /src && setsid nohup python3 serve/server.py --engine strata --config /data/strata-ud-q4_k_xl.json --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started'
sleep 12
docker exec strata166 bash -lc 'echo "[serve-run 头 6 行]"; head -6 /data/serve-run.log; echo "[进程]"; ps -eo pid,pcpu,args | grep -E "server\.py|build-906/strata" | grep -v grep'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=600)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('--- STDERR ---')
    print(r.stderr.decode('utf-8', 'replace')[:800])
