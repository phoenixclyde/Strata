# -*- coding: utf-8 -*-
"""在 166 上搭好 build-ctx 并后台启动 docker build（独立镜像 strata-gfx906:0.1.39）。
远端路径全部写死在本文件里（避开 Git Bash 的 argv 路径改写）。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
CTX = '/home/albus/strata166/build-ctx'
LOG = '/home/albus/strata166/logs/build-image.log'
DOCKERFILE_LOCAL = r'D:\strata166\docker\Dockerfile'


def ssh(script, timeout=600):
    b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
    cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
           '-i', KEY, HOST, 'base64 -d | bash']
    r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


df = open(DOCKERFILE_LOCAL, encoding='utf-8').read()
df_b64 = base64.b64encode(df.encode('utf-8')).decode('ascii')

IGNORE = "**\n!Dockerfile\n!transfer/\n!transfer/**\n"

script = r'''
set +e
CTX=%s
mkdir -p $CTX/transfer
cp -f /home/albus/strata166/transfer/strata-src-0.1.39.zip $CTX/transfer/
cp -f /home/albus/strata166/transfer/llama.cpp-3cf0325.tar.gz $CTX/transfer/
echo '%s' | base64 -d > $CTX/Dockerfile
printf '%s' > $CTX/.dockerignore
echo "=== ctx ==="; ls -l $CTX $CTX/transfer
echo "=== .dockerignore ==="; cat $CTX/.dockerignore
echo "=== 现有 docker 磁盘 ==="; df -h / | tail -1
echo "=== 底座镜像是否已在本地 ==="
docker images --format '{{.Repository}}:{{.Tag}}' | grep -i 'rocm-gfx906' || echo "  (本地没有，需要拉)"
echo "=== 后台启动 build ==="
cd /home/albus/strata166
nohup docker build --progress=plain -t strata-gfx906:0.1.39 -f $CTX/Dockerfile $CTX > %s 2>&1 &
echo "build pid=$!"
sleep 5
tail -5 %s
''' % (CTX, df_b64, IGNORE, LOG, LOG)

rc, out, err = ssh(script, timeout=900)
print(out)
if err.strip():
    print('ERR', err[:600])
print('rc=%s' % rc)
