# 诊断 -407：容器状态、日志尾部、端口监听、serve 进程
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
C=strata166-407
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "===== 容器状态 ====="
docker ps -a --filter name=strata166-40 --format '{{.Names}} | {{.Status}} | {{.Ports}}'
echo
echo "===== 日志尾部 25 行 ====="
tail -25 "$L"
echo
echo "===== 日志总行数 ====="
wc -l < "$L"
echo
echo "===== 容器内监听端口 ====="
docker exec $C sh -c 'ss -ltn 2>/dev/null | head -8 || netstat -ltn 2>/dev/null | head -8 || echo "(无 ss/netstat)"'
echo
echo "===== 容器内进程 ====="
docker exec $C sh -c 'ps -ef | grep -E "[s]erver.py|[s]trata " | head -6'
echo
echo "===== 宿主 8090 监听 ====="
ss -ltn 2>/dev/null | grep 8090 || echo "(宿主未见 8090)"
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=300)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
