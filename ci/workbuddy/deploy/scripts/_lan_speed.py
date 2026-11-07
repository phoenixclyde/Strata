# -*- coding: utf-8 -*-
"""测本机 -> 166 的内网吞吐，找出可用带宽（决定 111GB 怎么搬）。
   测法：不可压缩数据流到远端 /dev/null，分别测单流 / 换快密码 / 多条并行。"""
import os, subprocess, sys, threading, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

CHUNK = os.urandom(1 << 20)          # 1 MiB 不可压缩块，反复发
MB = int(sys.argv[1]) if len(sys.argv) > 1 else 200


def stream(nbytes, extra=None, label=''):
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY]
    cmd += (extra or [])
    cmd += [HOST, 'cat > /dev/null']
    t0 = time.time()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    sent = 0
    try:
        while sent < nbytes:
            k = min(len(CHUNK), nbytes - sent)
            p.stdin.write(CHUNK[:k])
            sent += k
        p.stdin.close()
    except (BrokenPipeError, OSError) as e:
        print('  %-28s BrokenPipe/OSError: %s' % (label, e))
    rc = p.wait()
    err = p.stderr.read().decode('utf-8', 'replace')
    dt = max(time.time() - t0, 1e-3)
    mbps = sent / 1048576 / dt
    print('  %-28s rc=%-3s %6.1f MB in %5.1fs = %6.2f MB/s  %s'
          % (label, rc, sent / 1048576, dt, mbps, err.strip()[:80]))
    return mbps


print('=== A) 单流，默认选项（%d MB）===' % MB)
a = stream(MB << 20, label='default')

print('=== B) 单流 + 快密码 + 关压缩（%d MB）===' % MB)
b = stream(MB << 20, extra=['-c', 'aes128-gcm@openssh.com', '-o', 'Compression=no'], label='aes128-gcm/nocomp')

print('=== C) 4 条并行（各 %d MB，合计 %d MB）===' % (MB // 2, MB * 2))
res = []
th = []
t0 = time.time()


def w(i):
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-c', 'aes128-gcm@openssh.com',
           '-o', 'Compression=no', '-i', KEY, HOST, 'cat > /dev/null']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    n = (MB // 2) << 20
    sent = 0
    try:
        while sent < n:
            k = min(len(CHUNK), n - sent)
            p.stdin.write(CHUNK[:k])
            sent += k
        p.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    p.wait()
    res.append(sent)


for i in range(4):
    t = threading.Thread(target=w, args=(i,))
    t.start()
    th.append(t)
for t in th:
    t.join()
dt = max(time.time() - t0, 1e-3)
tot = sum(res)
print('  4 条并行：%6.1f MB in %5.1fs = %6.2f MB/s (aggregate)' % (tot / 1048576, dt, tot / 1048576 / dt))
