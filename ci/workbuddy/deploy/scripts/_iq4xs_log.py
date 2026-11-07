# -*- coding: utf-8 -*-
"""把 IQ4_XS 的启动期关键行抽出来（专家缓存 / 常驻 / PLE / 读盘），用于与 UD-Q4 逐项对照。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
docker exec strata166-401 bash -lc '
echo "=== IQ4_XS 启动期关键行 ==="
grep -E "expert cache [0-9]+ slots|resident RAM mode|mapped pinned|PLE on|session is up|VRAM free|pre-filled|R4 hit path|expert-pool workers|draft head|blob reads|since the start" /data/strata-ud-iq4_xs.log | head -20
echo
echo "=== 全部 prompt/decode 计时行 ==="
grep -E "prompt [0-9]+ tokens =" /data/strata-ud-iq4_xs.log | tail -12
echo
echo "=== 最末 3 条 blob/file 统计 ==="
grep -E "resident RAM:|expert tiers:" /data/strata-ud-iq4_xs.log | tail -4
'
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:300])
