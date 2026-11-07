import os
import subprocess
import tarfile
import time

BASE = 'D:/workbuddy_space/strata_ws/albus/w828/'
SRC = BASE + 'up028'
TAR = BASE + 'up028.tgz'
HOST = 'albus@192.168.50.166'

os.makedirs(BASE, exist_ok=True)
t0 = time.time()
n = 0
with tarfile.open(TAR, 'w:gz', compresslevel=6) as t:
    for dp, dn, fn in os.walk(SRC):
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, SRC).replace('\\', '/')
            t.add(p, arcname=rel)
            n += 1
print('packed %d files, %.1f MB, %.1fs' % (n, os.path.getsize(TAR) / 1e6, time.time() - t0))

r = subprocess.run(['scp', '-o', 'BatchMode=yes', TAR, HOST + ':/home/albus/strata166/dl/up028.tgz'],
                   capture_output=True, text=True, timeout=900)
print('scp rc', r.returncode, r.stdout[-400:], r.stderr[-400:])
