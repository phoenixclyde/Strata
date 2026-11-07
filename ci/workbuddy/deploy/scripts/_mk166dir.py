# -*- coding: utf-8 -*-
"""在 166 上建专用目录 /home/albus/strata166（只建目录，不动任何既有服务/镜像）。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
OUT = r'D:\strata166\logs\_166_mkdir.txt'

SCRIPT = r'''
set +e
R=/home/albus/strata166
echo "=== 建目录 $R ==="
mkdir -p $R/docker $R/src $R/build $R/weights $R/data $R/logs $R/transfer
find $R -maxdepth 1 -type d | sort
echo
echo "=== 挂载/空间 ==="
df -h / /home /models 2>&1
echo
echo "=== 确认没碰任何既有东西 ==="
docker ps --format '{{.Names}}|{{.Status}}' | sort
echo "--- 镜像数量 ---"
docker images -q | wc -l
echo "--- routek-base 摘要（应与之前一致）---"
docker image inspect routek-base:gfx906-rocm101-hip716-torch215 --format '{{.Id}} {{.Created}}' 2>&1
echo
echo "=== 166 出网复测（构建要拉底座镜像）==="
for R2 in docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete; do
  printf '  %-56s ' "$R2"
  timeout 60 docker manifest inspect "$R2" >/tmp/_m.json 2>/tmp/_m.err
  echo "rc=$? size=$(wc -c </tmp/_m.json)B"
done
echo "--- Ubuntu apt 源可达性（镜像里要 apt install cmake/ninja）---"
grep -rhE '^deb ' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null | head -5
printf '  archive.ubuntu.com:80  '; timeout 8 bash -c 'echo > /dev/tcp/archive.ubuntu.com/80' 2>&1 && echo OK || echo NO
printf '  mirrors.tuna.tsinghua.edu.cn:80  '; timeout 8 bash -c 'echo > /dev/tcp/mirrors.tuna.tsinghua.edu.cn/80' 2>&1 && echo OK || echo NO
printf '  mirrors.aliyun.com:80  '; timeout 8 bash -c 'echo > /dev/tcp/mirrors.aliyun.com/80' 2>&1 && echo OK || echo NO
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY,
       'albus@192.168.50.166', 'base64 -d | bash']
t0 = time.time()
try:
    p = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=600)
    out, err, rc = p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace'), p.returncode
except subprocess.TimeoutExpired as e:
    out, err, rc = (e.stdout or b'').decode('utf-8', 'replace'), 'TIMEOUT', -1
open(OUT, 'w', encoding='utf-8').write('rc=%s %.1fs\n%s\n--- STDERR ---\n%s\n' % (rc, time.time() - t0, out, err))
print('rc=%s %.1fs' % (rc, time.time() - t0))
print(out)
