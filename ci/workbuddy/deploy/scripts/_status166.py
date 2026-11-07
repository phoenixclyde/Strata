# -*- coding: utf-8 -*-
"""查 166 侧当前状态：镜像构建进度 + 权重落盘进度 + 磁盘 + 容器（只读）。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 1) 镜像构建：进程 + 日志尾 ==="
pgrep -af "docker build" | head -3 || echo "  (没有 docker build 在跑)"
echo "--- build-image.log 尾 40 行 ---"
tail -40 /home/albus/strata166/logs/build-image.log
echo
echo "=== 2) 新镜像是否已生成 ==="
docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}' | grep -i strata || echo "  (还没有)"
echo
echo "=== 3) 权重落盘 ==="
ls -l /home/albus/strata166/weights/ 2>&1
du -sh /home/albus/strata166/weights 2>/dev/null
echo
echo "=== 4) 磁盘 / 内存 / GPU ==="
df -h / | tail -1
free -g | head -2
( rocm-smi --showmeminfo vram 2>&1 | grep -E 'VRAM Total' ) || echo "  rocm-smi 无输出"
echo
echo "=== 5) 现有容器（应仍为原来 5 个）==="
docker ps --format '{{.Names}}|{{.Status}}'
echo
echo "=== 6) docker 磁盘占用 ==="
docker system df 2>&1 | head -6
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=600)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:400])
