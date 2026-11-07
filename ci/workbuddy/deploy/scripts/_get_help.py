# -*- coding: utf-8 -*-
"""取容器里 strata 的 generate 帮助原文（权威），存回本机。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
docker exec strata166-401 bash -lc 'cd /src && ./build-906/strata --help 2>&1' | head -260
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
out = r.stdout.decode('utf-8', 'replace')
open(r'D:\strata166\logs\_strata_help.txt', 'w', encoding='utf-8').write(out)
print('captured %d chars' % len(out))
print(out[:3500])
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:300])
