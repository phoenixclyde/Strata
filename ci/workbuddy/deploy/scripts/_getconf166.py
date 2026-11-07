# -*- coding: utf-8 -*-
"""取 166 上现有配置与 UD-IQ4_XS 的官方启动参数原文，作为新配置模板。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 现有配置 /data/strata-ud-q4_k_xl.json ==="
cat /home/albus/strata166/data/strata-ud-q4_k_xl.json
echo
echo "=== /data 目录 ==="
ls -la /home/albus/strata166/data/ | head -30
echo
echo "=== weights 目录 ==="
ls -l /home/albus/strata166/weights/
echo
echo "=== 磁盘 ==="
df -h / | tail -1
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=180)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:300])
