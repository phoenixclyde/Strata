# 只读：查 pack 的结构与生成工具（切换现役的前置成本）
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
C=strata166-406
echo "=== A) 宿主 /data/packs ==="
ls -l /home/albus/strata166/data/packs/ 2>/dev/null
du -sh /home/albus/strata166/data/packs/* 2>/dev/null
echo "--- ud-iq4_xs 内容 ---"
ls -l /home/albus/strata166/data/packs/ud-iq4_xs/ 2>/dev/null | head -20
echo
echo "=== B) 容器内 /src 顶层 ==="
docker exec $C ls /src/ 2>/dev/null
echo "--- /src/tools ---"
docker exec $C ls /src/tools/ 2>/dev/null
echo
echo "=== C) 找 pack 生成入口（源码面）==="
docker exec $C sh -c "find /src -maxdepth 3 -iname '*pack*' 2>/dev/null | head -30" 2>/dev/null
echo "--- 源码里 pack 相关关键字 ---"
docker exec $C sh -c "grep -rl 'native projection' /src --include=*.cpp --include=*.h --include=*.py 2>/dev/null | head -10" 2>/dev/null
echo
echo "=== D) 现役容器启动命令行 ==="
docker inspect -f '{{json .Config.Cmd}} {{json .Config.Entrypoint}}' $C 2>/dev/null
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=300)
out = p.stdout.decode("utf-8", "replace")
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
