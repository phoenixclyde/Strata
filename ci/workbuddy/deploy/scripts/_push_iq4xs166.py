# -*- coding: utf-8 -*-
"""把 UD-IQ4_XS 三片推到 166（远端路径写死，绝不经命令行 —— MSYS 会改写 / 开头的 argv）。"""
import os, subprocess, sys, threading, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
R_WEIGHTS = '/home/albus/strata166/weights'
LOCAL_DIR = r'D:\idm\Strata-UDIQ4XS'
FILES = [os.path.join(LOCAL_DIR, 'Qwen3.8-Flash-Next-UD-IQ4_XS-0000%d-of-00003.gguf' % i) for i in (1, 2, 3)]


def ssh(script, timeout=3600):
    import base64
    b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
           '-i', KEY, HOST, 'base64 -d | bash']
    r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def remote_size(path):
    rc, out, _ = ssh('stat -c %%s %s 2>/dev/null || echo -1' % path, timeout=120)
    try:
        return int(out.strip().splitlines()[-1])
    except Exception:
        return -1


print('=== 166 磁盘 ===')
rc, out, _ = ssh('df -h / | tail -1; ls -l %s' % R_WEIGHTS, 120)
print(out)

ssh('mkdir -p %s' % R_WEIGHTS, timeout=120)

jobs = []
for f in FILES:
    name = os.path.basename(f)
    rp = '%s/%s' % (R_WEIGHTS, name)
    lsz = os.path.getsize(f)
    rsz = remote_size(rp)
    if rsz == lsz:
        print('  skip %-52s 远端已一致 (%.2f GB)' % (name, lsz / 1e9), flush=True)
        continue
    if rsz > 0:
        print('  %-52s 远端 %d/%d，删除后重传' % (name, rsz, lsz), flush=True)
        ssh('rm -f %s' % rp, timeout=300)
    jobs.append((f, rp, lsz))

if not jobs:
    print('全部已一致，无需传输')
else:
    total = sum(j[2] for j in jobs)
    print('  实际要传 %d 个文件，%.2f GB' % (len(jobs), total / 1e9), flush=True)
    done = [0]
    lock = threading.Lock()
    t0 = time.time()

    def mon():
        while done[0] < total:
            time.sleep(20)
            with lock:
                d = done[0]
            el = max(time.time() - t0, 1e-3)
            sp = d / 1048576 / el
            print('    [%s] %5.1f%%  %.2f/%.2f GB  avg %.1f MB/s  ETA %.1f min'
                  % (time.strftime('%H:%M:%S'), d * 100.0 / total, d / 1e9, total / 1e9, sp,
                     (total - d) / 1048576 / max(sp, .01) / 60), flush=True)

    def one(f, rp, lsz):
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
            print('  PIPE BROKEN %s: %s' % (os.path.basename(f), e), flush=True)
        rc = p.wait()
        err = p.stderr.read().decode('utf-8', 'replace').strip()
        print('  done %-52s rc=%s sent=%.2fGB %s' % (os.path.basename(f), rc, n / 1e9, err[:100]),
              flush=True)

    th = [threading.Thread(target=one, args=j) for j in jobs]
    threading.Thread(target=mon, daemon=True).start()
    for t in th:
        t.start()
    for t in th:
        t.join()
    el = time.time() - t0
    print('  === 传输结束 %.1f 分钟，平均 %.1f MB/s ===' % (el / 60, total / 1048576 / el), flush=True)

print()
print('=== 传后逐文件核 size ===')
for f in FILES:
    name = os.path.basename(f)
    rp = '%s/%s' % (R_WEIGHTS, name)
    lsz = os.path.getsize(f)
    rz = remote_size(rp)
    print('  %-52s 远端 %s / 本地 %s  %s' % (name, rz, lsz, 'OK' if rz == lsz else '**MISMATCH**'))
rc, out, _ = ssh('df -h / | tail -1', 120)
print('  166 磁盘:', out.strip())
