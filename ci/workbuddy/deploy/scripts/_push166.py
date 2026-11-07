# -*- coding: utf-8 -*-
"""把本机文件流式推到 166（tar over ssh，无临时服务）。用法：
    _push166.py <remote_dir> <local_path...>
输出进度（每 256MB）+ 传完在 166 上核 size。"""
import io, os, subprocess, sys, tarfile, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

remote_dir = sys.argv[1]
paths = sys.argv[2:]
if not paths:
    sys.exit('usage: _push166.py <remote_dir> <local_path...>')

total = 0
for p in paths:
    if os.path.isfile(p):
        total += os.path.getsize(p)
    else:
        for r, d, fs in os.walk(p):
            for f in fs:
                total += os.path.getsize(os.path.join(r, f))
print('push %d path(s), %.2f MB -> %s' % (len(paths), total / 1048576, remote_dir), flush=True)

cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
       '-o', 'ServerAliveInterval=30', '-i', KEY, HOST,
       'mkdir -p %s && tar xzf - -C %s && echo __PUSH_DONE__' % (remote_dir, remote_dir)]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

sent = [0]
last = [0.0]
t0 = time.time()


class Counter(io.RawIOBase):
    def __init__(self, f):
        self.f = f

    def writable(self):
        return True

    def write(self, b):
        try:
            p.stdin.write(b)
        except (BrokenPipeError, OSError):
            raise
        sent[0] += len(b)
        now = time.time()
        if now - last[0] > 5:
            last[0] = now
            el = max(now - t0, 1e-3)
            print('  %.1f%%  %.1f/%.1f MB  avg %.1f MB/s'
                  % (sent[0] * 100.0 / max(total, 1), sent[0] / 1048576, total / 1048576,
                     sent[0] / 1048576 / el), flush=True)
        return len(b)


cw = Counter(None)
try:
    with tarfile.open(fileobj=cw, mode='w|gz', compresslevel=1) as tf:
        for path in paths:
            base = os.path.basename(path.rstrip('\\/'))
            if os.path.isfile(path):
                tf.add(path, arcname=base)
            else:
                for r, d, fs in os.walk(path):
                    d[:] = [x for x in d if x not in ('.git', '__pycache__')]
                    for f in fs:
                        fp = os.path.join(r, f)
                        try:
                            tf.add(fp, arcname=os.path.join(base, os.path.relpath(fp, path)))
                        except OSError as e:
                            print('  skip', fp, e)
except BrokenPipeError:
    print('  BrokenPipe（远端先退出了）')
finally:
    try:
        p.stdin.close()
    except Exception:
        pass
out = p.stdout.read().decode('utf-8', 'replace')
err = p.stderr.read().decode('utf-8', 'replace')
rc = p.wait()
el = time.time() - t0
print('rc=%s  %.1fs  avg %.1f MB/s' % (rc, el, sent[0] / 1048576 / max(el, 1e-3)))
print('STDOUT:', out[-300:])
if err.strip():
    print('STDERR:', err[-800:])
