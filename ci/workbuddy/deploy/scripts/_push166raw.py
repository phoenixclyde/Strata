# -*- coding: utf-8 -*-
"""裸流并行推文件到 166（每文件一条 ssh `cat >`，无 tar/无压缩）。
用法：_push166raw.py <remote_dir> <local_file> [more...]
传完在 166 上核 size（可再核 sha256）。"""
import os, subprocess, sys, threading, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

remote_dir = sys.argv[1]
files = sys.argv[2:]
if not files:
    sys.exit('usage: _push166raw.py <remote_dir> <local_file...>')

subprocess.run([SSH, '-o', 'BatchMode=yes', '-i', KEY, HOST, 'mkdir -p %s' % remote_dir],
               check=False, capture_output=True)

total = sum(os.path.getsize(f) for f in files)
print('push %d file(s), %.2f GB -> %s' % (len(files), total / 1e9, remote_dir), flush=True)

t0 = time.time()
lock = threading.Lock()
done = [0]
prog = {f: [0] for f in files}


def stop():
    return any(not t.is_alive() for t in th) and done[0] >= total


def mon():
    while done[0] < total:
        time.sleep(20)
        el = max(time.time() - t0, 1e-3)
        with lock:
            d = done[0]
        print('  [%s] %5.1f%%  %.2f/%.2f GB  avg %.1f MB/s  ETA %.1f min'
              % (time.strftime('%H:%M:%S'), d * 100.0 / total, d / 1e9, total / 1e9,
                 d / 1048576 / el, (total - d) / 1048576 / max(d / 1048576 / el, .01) / 60), flush=True)


results = {}


def push(f):
    name = os.path.basename(f)
    rp = '%s/%s' % (remote_dir, name)
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
           '-i', KEY, HOST, 'cat > %s' % rp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    n = 0
    try:
        with open(f, 'rb') as fh:
            while True:
                b = fh.read(8 << 20)
                if not b:
                    break
                p.stdin.write(b)
                n += len(b)
                with lock:
                    done[0] += len(b)
        p.stdin.close()
    except (BrokenPipeError, OSError) as e:
        results[name] = 'pipe broken: %s' % e
    rc = p.wait()
    err = p.stderr.read().decode('utf-8', 'replace').strip()
    results[name] = 'rc=%s sent=%.2fGB %s' % (rc, n / 1e9, err[:120])
    print('  done %-54s %s' % (name, results[name]), flush=True)


th = [threading.Thread(target=push, args=(f,)) for f in files]
tm = threading.Thread(target=mon, daemon=True)
tm.start()
for t in th:
    t.start()
for t in th:
    t.join()

el = time.time() - t0
print('=== 推送结束 %.1f 分钟，平均 %.1f MB/s ===' % (el / 60, total / 1048576 / el))
for k, v in results.items():
    print('  %-54s %s' % (k, v))

# 远端核 size
print('=== 166 侧核对 ===')
names = ' '.join("'%s'" % os.path.basename(f) for f in files)
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-i', KEY, HOST,
                    'cd %s && ls -l %s && md5sum %s' % (remote_dir, names, names)],
                   capture_output=True, timeout=3600)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:400])
