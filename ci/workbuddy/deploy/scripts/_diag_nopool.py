# -*- coding: utf-8 -*-
"""补查 B6：--no-pool 为何 35 秒就退出（取未过滤的尾部输出）。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
C = 'strata166-401'

COMMON = ('--pack /data/packs/ud-iq4_xs '
          '--tokens-file /data/probe_tok.txt --max-new 4 '
          '--native /weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf '
          '--spec 4 --spec-min-p 0.5 '
          '--resident-budget-gib 76 --expert-profile /src/data/expert-profile.bin '
          '--expert-cache auto --max-context 131072 --kv int8 '
          '--prefill auto --stats --no-pool')

SC = ("docker exec %s bash -lc 'cd /src && ./build-906/strata %s; echo \"=== exit=$? ===\"' 2>&1 | tail -25"
      % (C, COMMON))
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:400])
