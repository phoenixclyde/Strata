# -*- coding: utf-8 -*-
"""进度快照：本机传输日志 + 166 构建日志/权重/镜像/磁盘。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

print('=== 本机时间 %s ===' % time.strftime('%H:%M:%S'))
p = r'D:\strata166\logs\_push_weights.txt'
t = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else '(无日志)'
print('--- 权重传输日志尾 12 行 ---')
print('\n'.join(t.strip().splitlines()[-12:]))
print()
print('=== 本机侧：待传文件当前大小 ===')
d = r'D:\idm\Strata-UDQ4KXL'
for f in sorted(os.listdir(d)):
    fp = os.path.join(d, f)
    if os.path.isfile(fp):
        print('  %-52s %10.2f GB' % (f, os.path.getsize(fp) / 1e9))

SCRIPT = r'''
set +e
echo "--- build-image.log 尾 22 行 ---"
tail -22 /home/albus/strata166/logs/build-image.log
echo
echo "--- docker build 进程 ---"
pgrep -af "docker build" | head -2 || echo "  (没有 build 在跑)"
echo
echo "--- 镜像 ---"
docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}' | grep -i strata || echo "  (strata 镜像还没有)"
echo
echo "--- 权重落盘 ---"
ls -l /home/albus/strata166/weights/ | tail -5
du -sh /home/albus/strata166/weights 2>/dev/null
echo
echo "--- 磁盘/内存 ---"
df -h / | tail -1; free -g | head -2
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=600)
print('=== 166 ===')
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:400])
