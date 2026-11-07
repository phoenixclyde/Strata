# -*- coding: utf-8 -*-
"""诊断 166 上 /data/mtp 的构成，以及 mtp_pack.py 读取清单的方式"""
import os, base64, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== /data/mtp 树（深度2） ==="
find /data/mtp -maxdepth 2 | head -60
echo
echo "=== 各条目大小 ==="
du -sh /data/mtp/* 2>/dev/null
echo
echo "=== 清单类文件 ==="
ls -l /data/mtp/*.json /data/mtp/*.txt 2>/dev/null
for f in /data/mtp/*.json; do
  [ -f "$f" ] || continue
  echo "--- $f (head 600) ---"
  head -c 600 "$f"; echo
done
echo
echo "=== tensors 目录（前 10 + 计数） ==="
ls -l /data/mtp/tensors 2>/dev/null | head -12
echo "count: $(ls /data/mtp/tensors 2>/dev/null | wc -l)"
echo
echo "=== mtp_pack.py 里涉及 file 字段与 json 的行 ==="
grep -n "json\|\[\"file\"\]\|\['file'\]\|glob\|iterdir" /src/tools/mtp_pack.py | head -30
echo
echo "=== mtp_rt.py 里涉及的输入参数 ==="
grep -n "argv\|argparse\|add_argument\|dense.txt" /src/tools/mtp_rt.py | head -30
echo
echo "=== 容器状态 ==="
docker ps --format "{{.Names}}|{{.Status}}|{{.Ports}}" | grep -i strata
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---')
    print(e[:800])
