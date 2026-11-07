# -*- coding: utf-8 -*-
"""修掉误写路径 + 用「远端路径写死」的裸流推送器（含断点续传 + 传后核 size）。

远端路径一律从本文件的常量取，**绝不来自命令行** ——
Git Bash(MSYS) 会把以 / 开头的 argv 改写成 Windows 路径（本次 6.3GB 误写的根因）。
"""
import os, subprocess, sys, threading, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

BOGUS = '/home/albus/C:'
R_TRANSFER = '/home/albus/strata166/transfer'
R_WEIGHTS = '/home/albus/strata166/weights'


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


def push(files, rdir):
    os.makedirs(os.path.dirname(files[0]) or '.', exist_ok=True)
    jobs = []
    for f in files:
        name = os.path.basename(f)
        rp = '%s/%s' % (rdir, name)
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
        return
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
            print('    [%s] %5.1f%%  %.2f/%.2f GB  avg %.1f MB/s  ETA %.1f min'
                  % (time.strftime('%H:%M:%S'), d * 100.0 / total, d / 1e9, total / 1e9,
                     d / 1048576 / el, (total - d) / 1048576 / max(d / 1048576 / el, .01) / 60),
                  flush=True)

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
    tm = threading.Thread(target=mon, daemon=True)
    tm.start()
    for t in th:
        t.start()
    for t in th:
        t.join()
    el = time.time() - t0
    print('  === 传输结束 %.1f 分钟，平均 %.1f MB/s ===' % (el / 60, total / 1048576 / el), flush=True)
    for f, rp, lsz in jobs:
        rz = remote_size(rp)
        print('  %-52s 远端 %s / 本地 %s  %s' % (os.path.basename(f), rz, lsz,
                                                'OK' if rz == lsz else 'MISMATCH'), flush=True)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('clean', 'all'):
        print('=== 1) 清掉误写的 %s ===' % BOGUS, flush=True)
        rc, out, err = ssh('du -sh "%s" 2>/dev/null; rm -rf "%s"; echo "rm rc=$?"; ls -d "%s" 2>&1'
                           % (BOGUS, BOGUS, BOGUS), timeout=900)
        print(out, err[:200], flush=True)
        rc, out, _ = ssh('df -h / | tail -1', timeout=120)
        print('  ', out.strip(), flush=True)
    if what in ('ctx', 'all'):
        print('=== 2) 传构建上下文 ===', flush=True)
        ssh('mkdir -p %s %s' % (R_TRANSFER, R_WEIGHTS), timeout=120)
        push([r'D:\strata166\transfer\strata-src-0.1.39.zip',
              r'D:\strata166\transfer\llama.cpp-3cf0325.tar.gz'], R_TRANSFER)
    if what == 'weights':
        print('=== 传权重（4 片并行）===', flush=True)
        ssh('mkdir -p %s' % R_WEIGHTS, timeout=120)
        push([r'D:\idm\Strata-UDQ4KXL\Qwen3.8-Flash-Next-UD-Q4_K_XL-0000%d-of-00004.gguf' % i
              for i in range(1, 5)], R_WEIGHTS)
