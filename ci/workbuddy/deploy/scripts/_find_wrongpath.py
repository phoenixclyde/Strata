# -*- coding: utf-8 -*-
"""查清 MSYS 改写后文件被写到了 166 的哪里，并清理这些残留目录。
（远端路径一律硬编码在脚本里，不经 Bash 参数，避免再次被改写。）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'

SCRIPT = r'''
set +e
echo "=== /home/albus 下一级（找异常的 C: 目录）==="
ls -la /home/albus | head -40
echo
echo "=== 找被误写的目录树 ==="
find /home/albus -maxdepth 3 -name "C:" -o -maxdepth 3 -type d -name "*PortableGit*" 2>/dev/null | head
echo
echo "=== /home/albus/C: 递归看看（若有）==="
if [ -d "/home/albus/C:" ]; then
  find "/home/albus/C:" -maxdepth 8 -type d | head -20
  echo "--- 里面的文件 ---"
  find "/home/albus/C:" -type f -printf '%10s  %p\n' 2>/dev/null | head -20
  echo "--- 合计 ---"
  du -sh "/home/albus/C:" 2>/dev/null
fi
echo
echo "=== 正确的目标目录（应为空或不存在）==="
ls -la /home/albus/strata166/weights /home/albus/strata166/transfer 2>&1
echo
echo "=== 磁盘 ==="
df -h / | tail -1
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-i', KEY, 'albus@192.168.50.166', 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=600)
out = r.stdout.decode('utf-8', 'replace')
print(out)
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:400])
open(r'D:\strata166\logs\_166_wrongpath.txt', 'w', encoding='utf-8').write(out)
