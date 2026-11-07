# -*- coding: utf-8 -*-
"""166 现场：容器 402 的启动配置 / data 目录 / 引擎日志 / 版本"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "===== [1] date / uptime ====="
date -Is; uptime
echo
echo "===== [2] docker ps -a (strata) ====="
docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}' | grep -i strata
echo
echo "===== [3] container 402 启动配置 ====="
docker inspect strata166-402 --format 'Cmd={{.Config.Cmd}}
Image={{.Config.Image}}
Restart={{.HostConfig.RestartPolicy.Name}}
Ports={{.HostConfig.PortBindings}}
Mounts={{range .Mounts}}{{.Source}}=>{{.Destination}}({{.Mode}}) {{end}}
Env={{range .Config.Env}}{{.}} {{end}}' 2>&1
echo
echo "===== [4] /home/albus/strata166/data 内容 ====="
ls -la /home/albus/strata166/data/ 2>&1 | head -30
echo
echo "===== [5] 哪个 config 在用 ====="
for f in /home/albus/strata166/data/*.json; do
  echo "--- $f ---"; cat "$f"
done
echo
echo "===== [6] 容器内进程 ====="
docker exec strata166-402 bash -lc 'ps -eo pid,ppid,etime,pcpu,rss,args --sort=-pcpu | head -12' 2>&1
echo
echo "===== [7] /src 下 build 目录 ====="
docker exec strata166-402 bash -lc 'ls -d /src/build* 2>&1; ls -la /src/build-906/strata 2>&1' 2>&1
echo
echo "===== [8] 引擎版本 ====="
docker exec strata166-402 bash -lc '/src/build-906/strata --version 2>&1 | head -3' 2>&1
echo
echo "===== [9] /v1/models ====="
curl -s --max-time 30 http://127.0.0.1:8090/v1/models
echo
echo "===== [10] 引擎日志文件 ====="
ls -la /home/albus/strata166/data/*.log 2>&1
echo
echo "===== [11] 最近 5 条 prompt 计时 ====="
docker exec strata166-402 bash -lc 'grep -E "prompt [0-9]+ tokens" /data/strata-ud-iq4_xs.log 2>/dev/null | tail -5; echo ---; grep -E "prompt [0-9]+ tokens" /data/strata-ud-q4_k_xl.log 2>/dev/null | tail -5' 2>&1
echo
echo "===== [12] GPU / VRAM / 内存 / 磁盘 ====="
rocm-smi --showmeminfo vram 2>/dev/null | head -8
echo ---
free -g | head -2
echo ---
df -h / | tail -1
echo
echo "===== [13] weights 目录 ====="
ls -la /home/albus/strata166/weights/ 2>&1 | head -20
echo
echo "===== [14] 全部镜像 ====="
docker images --format '{{.Repository}}:{{.Tag}}|{{.ID}}|{{.Size}}' | grep -i strata
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b64.encode('ascii'), capture_output=True, timeout=600)
out = r.stdout.decode('utf-8', 'replace')
with open(r'D:/workbuddy/_z_rk81/_pr108.out.txt', 'w', encoding='utf-8') as f:
    f.write(out)
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:800])
print(out)
