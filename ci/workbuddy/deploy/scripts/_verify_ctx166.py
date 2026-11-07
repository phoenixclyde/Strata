# -*- coding: utf-8 -*-
"""核对传入 166 的构建上下文与本地是否逐字节一致（sha256 对拍）。"""
import base64, hashlib, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
FILES = ['strata-src-0.1.39.zip', 'llama.cpp-3cf0325.tar.gz']
LOCAL = r'D:\strata166\transfer'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


print('=== 本地 ===')
loc = {}
for n in FILES:
    p = os.path.join(LOCAL, n)
    loc[n] = sha(p)
    print('  %-34s %s  %8.2f MB' % (n, loc[n][:32], os.path.getsize(p) / 1048576))

script = 'cd /home/albus/strata166/transfer && for f in %s; do printf "%%s " "$f"; sha256sum "$f" | cut -c1-64; done' % ' '.join(FILES)
b64 = base64.b64encode(script.encode()).decode()
cmd = [SSH, '-o', 'BatchMode=yes', '-i', KEY, 'albus@192.168.50.166', 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode(), capture_output=True, timeout=300)
print('=== 166 ===')
rem = {}
for line in r.stdout.decode('utf-8', 'replace').splitlines():
    parts = line.split()
    if len(parts) == 2:
        rem[parts[0]] = parts[1]
        print('  %-34s %s' % (parts[0], parts[1][:32]))
if r.stderr.strip():
    print('ERR', r.stderr.decode()[:300])

print('=== 判定 ===')
for n in FILES:
    ok = rem.get(n) == loc[n]
    print('  %-34s %s' % (n, 'IDENTICAL' if ok else 'MISMATCH  local=%s remote=%s'
                          % (loc[n][:16], (rem.get(n) or '?')[:16])))
