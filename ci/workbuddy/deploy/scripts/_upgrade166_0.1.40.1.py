# -*- coding: utf-8 -*-
"""升级 166 到 Strata 0.1.40.1：推送构建上下文 → 后台 docker build → 轮询

远端路径写死在常量里（绝不经命令行 —— MSYS 会把 / 开头 argv 改写成 Windows 路径）。
"""
import base64, os, subprocess, sys, threading, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

R_CTX = '/home/albus/strata166/build-ctx-401'
TAG = 'strata-gfx906:0.1.40.1'
LOG = '/home/albus/strata166/logs/build-image-401.log'

LOCAL = [
    (r'D:\strata166\docker\Dockerfile-0.1.40.1', 'Dockerfile'),
    (r'D:\strata166\docker\patch_gfx906.py',      'patch_gfx906.py'),
    (r'D:\strata166\transfer\strata-src-0.1.40.1.zip', 'transfer/strata-src-0.1.40.1.zip'),
    (r'D:\strata166\transfer\llama.cpp-3cf0325.tar.gz', 'transfer/llama.cpp-3cf0325.tar.gz'),
]


def ssh(script, timeout=3600):
    b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
           '-i', KEY, HOST, 'base64 -d | bash']
    r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def rsize(path):
    rc, out, _ = ssh('stat -c %%s %s 2>/dev/null || echo -1' % path, timeout=120)
    try:
        return int(out.strip().splitlines()[-1])
    except Exception:
        return -1


print('=== 1) 建远端构建上下文（只放需要的东西，避免把 111GB 权重当上下文）===')
rc, out, err = ssh('set -e; mkdir -p %s %s %s; ls -la %s' % (R_CTX, R_CTX + '/transfer',
                                                            '/home/albus/strata166/logs', R_CTX))
print(out[-600:], err[:200])

print('=== 2) 推送 4 个文件 ===')
jobs = []
for lp, rel in LOCAL:
    rp = '%s/%s' % (R_CTX, rel)
    lsz = os.path.getsize(lp)
    rsz = rsize(rp)
    if rsz == lsz:
        print('  skip %-46s 远端已一致 (%d B)' % (rel, lsz))
        continue
    if rsz > 0:
        ssh('rm -f %s' % rp, timeout=120)
    jobs.append((lp, rp, lsz, rel))
if jobs:
    ssh('mkdir -p %s/transfer' % R_CTX, timeout=120)
for lp, rp, lsz, rel in jobs:
    t0 = time.time()
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
           '-i', KEY, HOST, 'cat > %s' % rp]
    with open(lp, 'rb') as fh:
        r = subprocess.run(cmd, stdin=fh, capture_output=True, timeout=900)
    dt = max(time.time() - t0, 1e-3)
    rz = rsize(rp)
    print('  %-46s %10d B  %.1fs  %.1f MB/s  远端=%d %s'
          % (rel, lsz, dt, lsz / 1048576 / dt, rz, 'OK' if rz == lsz else '**MISMATCH**'))

print('=== 3) 后台启动 docker build ===')
BUILD = r'''
set +e
cd %s
setsid nohup docker build --progress=plain -f Dockerfile -t %s . > %s 2>&1 < /dev/null &
echo "build_started pid=$!"
sleep 8
echo "--- 头几行 ---"
head -20 %s
''' % (R_CTX, TAG, LOG, LOG)
rc, out, err = ssh(BUILD, timeout=300)
print(out, err[:300])

print('=== 4) 轮询（每 45s 一次，最多 60 轮 = 45 分钟）===')
t0 = time.time()
for i in range(60):
    time.sleep(45)
    rc, out, _ = ssh(
        'echo "--- T+%ds ---"; grep -E "^#[0-9]+ \\[|DONE|ERROR|error:|FAIL-CLOSED|Successfully|writing image|naming to" %s | tail -12; '
        'echo "[tail]"; tail -3 %s; echo "[img]"; docker images --format "{{.Repository}}:{{.Tag}}|{{.Size}}" | grep -i strata'
        % (int(time.time() - t0), LOG, LOG), timeout=180)
    print(out.rstrip())
    if 'naming to' in out or ('strata-gfx906:0.1.40.1' in out and 'GB' in out):
        print('### BUILD 似乎完成 ###')
        break
    if 'FAIL-CLOSED' in out or 'ERROR: failed to solve' in out:
        print('### BUILD 失败 ###')
        break
print('=== 5) 最终 tail ===')
rc, out, _ = ssh('tail -40 %s' % LOG, timeout=180)
print(out)
