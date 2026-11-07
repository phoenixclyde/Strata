# -*- coding: utf-8 -*-
"""用 --progress=plain 重放 0.1.40.1 构建：前 11 步走缓存，只重跑失败的第 12 步，抓完整输出。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
LOG = '/home/albus/strata166/logs/build401-replay.log'
CTX = '/home/albus/strata166/build-ctx-401'


def ssh(script, timeout=900):
    b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
           '-i', KEY, HOST, 'base64 -d | bash']
    r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


sc = r'''
set +e
echo "=== Dockerfile 行数/内容指纹 ==="
wc -l %(ctx)s/Dockerfile
md5sum %(ctx)s/Dockerfile %(ctx)s/patch_gfx906.py
echo
echo "=== sed -n '44,52p' Dockerfile（含行号）==="
sed -n '44,52p' %(ctx)s/Dockerfile | cat -A | head -20
echo
echo "=== 重放构建（plain）==="
cd %(ctx)s
docker build --progress=plain -f Dockerfile -t strata-gfx906:0.1.40.1 . > %(log)s 2>&1
echo "build_rc=$?"
echo "=== 日志尾 80 行 ==="
tail -80 %(log)s
''' % {'ctx': CTX, 'log': LOG}

rc, out, err = ssh(sc, timeout=900)
print('ssh rc =', rc)
print(out)
if err.strip():
    print('--- stderr ---')
    print(err[:1500])
