# -*- coding: utf-8 -*-
"""只读：取 strata166 容器的完整定义（供照抄起 0.1.40.1 容器）+ 看构建进度"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

def ssh(sc, t=300):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')

SC = r'''
echo "=== 构建进度 ==="
grep -E "^#[0-9]+ \[|DONE|ERROR|error:|FAIL-CLOSED|PATCH_V2_OK|naming to|writing image" /home/albus/strata166/logs/build-image-401.log | tail -14
echo "[tail]"; tail -4 /home/albus/strata166/logs/build-image-401.log
echo
echo "=== 现有容器 strata166 的定义（照抄用）==="
docker inspect strata166 --format '{{.Config.Image}}' 2>/dev/null || echo "(容器不在)"
docker inspect strata166 --format '{{json .HostConfig.Devices}}' 2>/dev/null
docker inspect strata166 --format '{{json .HostConfig.GroupAdd}}' 2>/dev/null
docker inspect strata166 --format '{{json .HostConfig.Binds}}' 2>/dev/null
docker inspect strata166 --format 'IpcMode={{.HostConfig.IpcMode}} Ulimits={{json .HostConfig.Ulimits}} Ports={{json .HostConfig.PortBindings}}' 2>/dev/null
docker inspect strata166 --format '{{json .Config.Env}}' 2>/dev/null
docker inspect strata166 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}}' 2>/dev/null
echo
echo "=== /data 下的配置文件 ==="
ls -l /home/albus/strata166/data/*.json
echo "--- strata-ud-q4_k_xl.json ---"
cat /home/albus/strata166/data/strata-ud-q4_k_xl.json
echo
echo "=== 镜像清单 ==="
docker images --format "{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}" | grep -i strata
echo
echo "=== 磁盘 / 内存 ==="
df -h / | tail -1; free -g | head -2
'''
out, err = ssh(SC, 300)
print(out)
if err.strip():
    print('[stderr]', err.strip()[:300])
