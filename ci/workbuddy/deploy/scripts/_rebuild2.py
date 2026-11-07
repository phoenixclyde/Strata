# -*- coding: utf-8 -*-
"""把补丁化的 Dockerfile + patch_hipcompat.py 推到 166 的 build-ctx，并重启构建。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
CTX = '/home/albus/strata166/build-ctx'
LOG = '/home/albus/strata166/logs/build-image.log'

df = open(r'D:\strata166\docker\Dockerfile', encoding='utf-8').read()
pt = open(r'D:\strata166\docker\patch_hipcompat.py', encoding='utf-8').read()
IGNORE = "**\n!Dockerfile\n!patch_hipcompat.py\n!transfer/\n!transfer/**\n"

script = """set +e
CTX=%s
echo '%s' | base64 -d > $CTX/Dockerfile
echo '%s' | base64 -d > $CTX/patch_hipcompat.py
echo '%s' | base64 -d > $CTX/.dockerignore
echo "=== .dockerignore ==="; cat $CTX/.dockerignore
echo "=== Dockerfile 关键行 ==="; grep -n 'patch_hipcompat\\|SMMQ_KQUANTS\\|STRATA_HIP_GFX906\\|FROM ' $CTX/Dockerfile
echo "=== patch 脚本语法检查 ==="
python3 -c "import ast; ast.parse(open('$CTX/patch_hipcompat.py').read()); print('OK')"
echo
echo "=== 重建 ==="
cd /home/albus/strata166
setsid nohup docker build --progress=plain -t strata-gfx906:0.1.39 -f $CTX/Dockerfile $CTX \\
  > %s 2>&1 < /dev/null &
echo "launched pid=$!"
sleep 40
tail -14 %s
""" % (CTX,
       base64.b64encode(df.encode('utf-8')).decode('ascii'),
       base64.b64encode(pt.encode('utf-8')).decode('ascii'),
       base64.b64encode(IGNORE.encode('utf-8')).decode('ascii'),
       LOG, LOG)

b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:600])
