# -*- coding: utf-8 -*-
"""进度快照 v2：166 侧 sha256 校验结果 + 构建进度 + 磁盘/内存。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 1) 权重 sha256 校验（166 侧）==="
cat /home/albus/strata166/logs/verify-weights.log 2>&1
echo "--- 期望值（setup.py UNSLOTH_SHARDS）---"
echo "  00001 4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082"
echo "  00002 3f342f1c1580473f1ee94ddd5b28206e8c07a70fa1a366f59d1d6c922919a6c9"
echo "  00003 56758f40269cad5cd9b0d3d6fbae0f40f6d5be6de49e4ab392dbe83157d9cbd3"
echo "  00004 753bda48b98ba4f1636134a90a967de1b2d3908a236c026e464777342e53510a"
echo "--- sha256 进程 ---"
pgrep -af _vfix.sh | head -2 || echo "  (已结束)"
echo
echo "=== 2) 镜像构建 ==="
echo "--- 进程 ---"; pgrep -af "docker build" | head -2 || echo "  (没有在跑)"
echo "--- 构建处于第几步（最近的 RUN/[N/9]）---"
grep -E '^#[0-9]+ \[|DONE|ERROR|error' /home/albus/strata166/logs/build-image.log | tail -14
echo "--- 日志最后 8 行 ---"
tail -8 /home/albus/strata166/logs/build-image.log
echo
echo "=== 3) 镜像是否产出 ==="
docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}' | grep -i strata || echo "  (还没有)"
echo
echo "=== 4) 资源 ==="
df -h / | tail -1
free -g | head -2
echo "=== 5) 容器（应仍为 5 个）==="
docker ps --format '{{.Names}}' | sort | tr '\n' ' '; echo
echo "=== 6) 编译进程（ninja/cc1plus 之类）==="
pgrep -af "ninja|cc1plus|clang|hipcc" | head -5 || echo "  (没有编译进程)"
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=600)
print('=== 本机时间 %s ===' % time.strftime('%H:%M:%S'))
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:400])
