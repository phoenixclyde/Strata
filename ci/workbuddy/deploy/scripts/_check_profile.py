# -*- coding: utf-8 -*-
"""查 expert-profile.bin 的来源：是否在源码 zip 里 / 在老容器里 / 在宿主机上"""
import base64, os, subprocess, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

def ssh(sc, t=300):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')

print('=== ① 0.1.40.1 zip 里有没有 data/ 与 expert-profile.bin ===')
z = zipfile.ZipFile(r'D:\strata166\transfer\strata-src-0.1.40.1.zip')
hits = [n for n in z.namelist() if '/data/' in n]
print('  data/ 下条目 %d 个:' % len(hits))
for n in hits[:20]:
    print('   ', n)
print('  expert-profile.bin 命中:', [n for n in z.namelist() if 'expert-profile' in n])

print()
print('=== ② 0.1.39 本地树里有没有 ===')
lp = r'D:\Strata\src\Strata-0.1.39\data'
if os.path.isdir(lp):
    for f in sorted(os.listdir(lp))[:20]:
        q = os.path.join(lp, f)
        print('   %-40s %s' % (f, os.path.getsize(q) if os.path.isfile(q) else 'DIR'))
else:
    print('  (无 data 目录)')

print()
print('=== ③ 166 上：老容器内 /src/data、宿主机 /home/albus/strata166/data ===')
o, e = ssh(r'''
echo "--- 老容器 strata166 内 /src/data ---"
docker exec strata166 bash -lc 'ls -l /src/data/ 2>/dev/null | head -20' 2>/dev/null || echo "(容器未运行，跳过 exec)"
echo "--- 镜像里有没有（不依赖容器运行）---"
docker run --rm --entrypoint sh strata-gfx906:0.1.39 -c 'ls -l /src/data/ 2>/dev/null | head -20; echo "---"; ls -l /src/data/expert-profile.bin 2>/dev/null || echo NO_PROFILE_IN_IMAGE'
echo "--- 宿主机 /home/albus/strata166/data ---"
ls -l /home/albus/strata166/data/ | head -20
''', 600)
print(o)
if e.strip():
    print('[stderr]', e.strip()[:300])
