import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
C = 'strata166-401'

sc = r'''
set +e
echo "=== 容器/进程 ==="
docker ps --format "{{.Names}}|{{.Status}}|{{.Image}}" | grep -i strata
echo
echo "=== 引擎启动 argv（含 kv/prefill/ctx） ==="
docker exec %(c)s bash -lc "ps -eo pid,etime,args | grep -E '[s]trata --serve'" 2>&1 | head -3
echo
echo "=== 本次会话 expert cache / resident 行（最后 12 条） ==="
docker exec %(c)s bash -lc "grep -E 'expert cache|resident RAM|slots|FilesExpertSource|FileExpertSource' /data/strata-ud-iq4_xs.log | tail -12" 2>&1
echo
echo "=== 显存 ==="
rocm-smi --showmemuse 2>/dev/null | grep -i vram | head -2
echo
echo "=== 磁盘 ==="
df -h / | tail -1
''' % {'c': C}

b = base64.b64encode(sc.encode()).decode()
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY,
                    'albus@192.168.50.166', 'base64 -d | bash'],
                   input=b.encode(), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('STDERR', e[:400])
