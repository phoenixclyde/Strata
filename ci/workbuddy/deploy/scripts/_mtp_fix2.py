# -*- coding: utf-8 -*-
"""在容器内诊断 /data/mtp，并查挂载映射"""
import os, base64, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 容器挂载映射 ==="
docker inspect strata166 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}}){{"\n"}}{{end}}'
echo
echo "=== 容器内 /data 树（深度2） ==="
docker exec strata166 bash -lc 'find /data -maxdepth 2 2>/dev/null | head -60'
echo
echo "=== du ==="
docker exec strata166 bash -lc 'du -sh /data/* 2>/dev/null'
echo
echo "=== 清单文件 ==="
docker exec strata166 bash -lc 'ls -l /data/mtp/*.json /data/mtp/*.txt 2>/dev/null; for f in /data/mtp/*.json; do [ -f "$f" ] || continue; echo "--- $f ---"; head -c 700 "$f"; echo; done'
echo
echo "=== tensors 目录 ==="
docker exec strata166 bash -lc 'ls -l /data/mtp/tensors 2>/dev/null | head -12; echo "count: $(ls /data/mtp/tensors 2>/dev/null | wc -l)"'
echo
echo "=== mtp_pack.py 关键行 ==="
docker exec strata166 bash -lc 'grep -n "json\|\"file\"\|glob\|iterdir\|tensors" /src/tools/mtp_pack.py | head -30'
echo
echo "=== mtp_rt.py 关键行 ==="
docker exec strata166 bash -lc 'grep -n "argv\|add_argument\|dense.txt\|def main" /src/tools/mtp_rt.py | head -30'
echo
echo "=== mtp_pack 用法 ==="
docker exec strata166 bash -lc 'cd /src && python3 tools/mtp_pack.py --help 2>&1 | head -25'
echo
echo "=== mtp_rt 用法 ==="
docker exec strata166 bash -lc 'cd /src && python3 tools/mtp_rt.py --help 2>&1 | head -25'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---')
    print(e[:800])
