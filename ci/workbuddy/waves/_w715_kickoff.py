# 启动 huihui pack 生成（后台）+ 侦察 vision 编译与装配（内层命令一律单引号，防外层展开）
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

SC = r'''set -u
C=strata166-406
GG=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
OUT=/data/packs/huihui-ud-iq4_xs
LOG=/data/_iqpack_huihui.log

echo "===== 0) 工具链检查 ====="
docker exec $C sh -c 'for t in cmake ninja g++ make python3; do printf "%s: " "$t"; command -v "$t" || echo MISSING; done'
echo
echo "===== 1) 启动 huihui pack 生成 ====="
if [ -f "/home/albus/strata166/data/packs/huihui-ud-iq4_xs/native_experts.txt" ]; then
  echo "已完成，跳过"
else
  docker exec -d $C sh -c "cd /src && python3 tools/iq_pack.py --gguf '$GG' --out '$OUT' --compat-bf16 > '$LOG' 2>&1"
  sleep 8
  echo "--- 日志 ---"; tail -c 1000 "$LOG" 2>/dev/null || echo "(暂无)"
  echo "--- 进程数 ---"; docker exec $C sh -c 'ps -ef | grep -c "[i]q_pack"'
  echo "--- 目标目录 ---"; ls -l /home/albus/strata166/data/packs/huihui-ud-iq4_xs/ 2>/dev/null || echo "(尚未创建)"
fi
echo
echo "===== 2) tools/vision/CMakeLists.txt ====="
docker exec $C sh -c 'cat /src/tools/vision/CMakeLists.txt'
echo
echo "===== 3) runconfig.py 里 vision 段的键定义 ====="
docker exec $C sh -c 'grep -n -B6 -A35 vision /src/serve/runconfig.py | head -100'
echo
echo "===== 4) server.py Vision 类装配段 ====="
docker exec $C sh -c 'sed -n "1818,1880p" /src/serve/server.py'
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=900)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_kickoff.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
