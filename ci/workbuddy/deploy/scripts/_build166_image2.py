# -*- coding: utf-8 -*-
"""在 166 上搭好 build-ctx 并后台启动 docker build（独立镜像 strata-gfx906:0.1.39）。
远端路径与所有内容一律 base64 传入，不经 shell 引号/argv 改写。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
CTX = '/home/albus/strata166/build-ctx'
LOG = '/home/albus/strata166/logs/build-image.log'

df = open(r'D:\strata166\docker\Dockerfile', encoding='utf-8').read()
IGNORE = "**\n!Dockerfile\n!transfer/\n!transfer/**\n"

script = '''set +e
CTX=%s
mkdir -p $CTX/transfer
cp -f /home/albus/strata166/transfer/strata-src-0.1.39.zip $CTX/transfer/
cp -f /home/albus/strata166/transfer/llama.cpp-3cf0325.tar.gz $CTX/transfer/
echo '%s' | base64 -d > $CTX/Dockerfile
echo '%s' | base64 -d > $CTX/.dockerignore
echo "=== build-ctx ==="; ls -l $CTX $CTX/transfer
echo "=== .dockerignore ==="; cat -A $CTX/.dockerignore | head
echo "=== 磁盘 ==="; df -h / | tail -1
echo "=== 本地是否已有底座 ==="
docker images --format '{{.Repository}}:{{.Tag}}' | grep -i 'rocm-gfx906' || echo "  (需拉取)"
echo "=== 启动 build（setsid 后台，脱离 ssh）==="
cd /home/albus/strata166
setsid nohup docker build --progress=plain -t strata-gfx906:0.1.39 -f $CTX/Dockerfile $CTX \\
  > %s 2>&1 < /dev/null &
echo "launched pid=$!"
sleep 8
echo "--- log head ---"
head -20 %s
''' % (
    CTX,
    base64.b64encode(df.encode('utf-8')).decode('ascii'),
    base64.b64encode(IGNORE.encode('utf-8')).decode('ascii'),
    LOG, LOG)

b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
out, err = r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')
print(out)
if err.strip():
    print('ERR', err[:800])
print('rc=%s' % r.returncode)
