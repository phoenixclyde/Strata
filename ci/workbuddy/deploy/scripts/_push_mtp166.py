# -*- coding: utf-8 -*-
"""把本机已有的 MTP 原始张量（base 模型的，5.2GB）目录树推到 166（保留相对路径）。
远端路径写死，避免 Git Bash argv 改写。"""
import base64, os, subprocess, sys, threading, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
LOCAL = r'D:\Strata\src\Strata-data\mtp'
REMOTE = '/home/albus/strata166/data/mtp'
WORKERS = 6

# 只推这两类（tensors/ 目录 + 两个 json）；不带 rt/ 与 mtp-q2_0.gguf（在 166 上重新生成）
jobs = []
for f in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, f)
    if f == 'tensors':
        for t in sorted(os.listdir(p)):
            tp = os.path.join(p, t)
            if os.path.isfile(tp):
                jobs.append((tp, REMOTE + '/tensors/' + t))
    elif f.endswith('.json'):
        jobs.append((p, REMOTE + '/' + f))

total = sum(os.path.getsize(a) for a, _ in jobs)
print('要推 %d 个文件，%.3f GB -> %s' % (len(jobs), total / 1e9, REMOTE), flush=True)


def ssh(script, timeout=1800):
    b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
           '-i', KEY, HOST, 'base64 -d | bash']
    return subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=timeout)


r = ssh('mkdir -p %s/tensors && echo ok' % REMOTE)
print('mkdir:', r.stdout.decode().strip(), r.stderr.decode()[:200])

done = [0]
lock = threading.Lock()
t0 = time.time()
fails = []


def one(local, remote):
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
           '-i', KEY, HOST, 'cat > %s' % remote]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    n = 0
    try:
        with open(local, 'rb') as fh:
            while True:
                b = fh.read(4 << 20)
                if not b:
                    break
                p.stdin.write(b)
                n += len(b)
        p.stdin.close()
    except (BrokenPipeError, OSError) as e:
        fails.append((remote, str(e)))
    rc = p.wait()
    err = p.stderr.read().decode('utf-8', 'replace').strip()
    if rc != 0 or n != os.path.getsize(local):
        fails.append((remote, 'rc=%s sent=%d/%d %s' % (rc, n, os.path.getsize(local), err[:80])))
    with lock:
        done[0] += n


ths = []
for a, b in jobs:
    while sum(1 for t in ths if t.is_alive()) >= WORKERS:
        time.sleep(0.2)
    t = threading.Thread(target=one, args=(a, b))
    t.start()
    ths.append(t)
for t in ths:
    t.join()
el = time.time() - t0
print('推送结束 %.1f s，%.3f GB，平均 %.1f MB/s' % (el, done[0] / 1e9, done[0] / 1048576 / max(el, 1e-3)))
if fails:
    print('失败 %d 个：' % len(fails))
    for f in fails[:10]:
        print('  ', f)
else:
    print('全部成功')

r = ssh('ls -l %s | head -5; echo ---; ls %s/tensors | wc -l; du -sh %s' % (REMOTE, REMOTE, REMOTE))
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:300])
