import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
C = 'strata166-401'

sc = r'''
set +e
echo "=== expert cache 启动横幅（filling / slots） ==="
docker exec %(c)s bash -lc "grep -nE 'filling the GPU|expert cache .*slots|slots,' /data/strata-ud-iq4_xs.log | tail -8" 2>&1
echo
echo "=== RAM budget / 分工行 ==="
docker exec %(c)s bash -lc "grep -nE 'RAM budget|of experts the GPU cache does not hold|resident RAM mode|pinned' /data/strata-ud-iq4_xs.log | tail -8" 2>&1
echo
echo "=== 最近一次启动头部（找 session is up 前后） ==="
docker exec %(c)s bash -lc "grep -nE 'session is up|GPU 0:|PLE on|R4 hit path|KV|kv ' /data/strata-ud-iq4_xs.log | tail -10" 2>&1
''' % {'c': C}

b = base64.b64encode(sc.encode()).decode()
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY,
                    'albus@192.168.50.166', 'base64 -d | bash'],
                   input=b.encode(), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('STDERR', e[:400])
