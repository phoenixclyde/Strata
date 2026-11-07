# -*- coding: utf-8 -*-
"""收尾快照：pack 内容（A4 是否留下 experts.bin）、磁盘、服务、残留进程。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
set +e
echo "=== 服务 ==="
docker exec strata166-401 bash -lc 'curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8090/v1/models'
docker exec strata166-401 bash -lc "ps -eo pid,etime,args | grep -E '[s]erver\.py|[s]trata --serve' | head -3"
echo
echo "=== pack 内容（看有没有 A4 留下的 experts.bin）==="
docker exec strata166-401 bash -lc 'ls -l /data/packs/ud-iq4_xs/'
echo
echo "=== 我留下的探针文件 ==="
docker exec strata166-401 bash -lc 'ls -l /data/probe_tok.txt /data/strata-ud-iq4_xs.json 2>&1'
echo
echo "=== 磁盘 ==="
df -h / | tail -1
echo
echo "=== 容器 ==="
docker ps -a --format '{{.Names}}|{{.Status}}' | grep -i strata
echo
echo "=== 是否还有我起的临时进程 ==="
pgrep -af "httpserver|http.server" | head -3 || echo "(无临时 http 服务)"
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:300])
