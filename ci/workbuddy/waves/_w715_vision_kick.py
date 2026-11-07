# 启动 strata-vision 编译（后台，产物落 /data/vision 持久）+ 查 runconfig SPEC 里 vision 的键定义
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

SC = r'''set -u
C=strata166-406
echo "===== 0) 主机 CPU / 核数 ====="
nproc; lscpu 2>/dev/null | grep -iE 'model name|avx512' | head -3
echo
echo "===== 1) 启动 strata-vision 编译（detached, AVX2 基线 PORTABLE=ON）====="
VLOG=/data/_vision_build.log
if [ -x /home/albus/strata166/data/vision/strata-vision ]; then
  echo "已存在，跳过: $(ls -l /home/albus/strata166/data/vision/strata-vision)"
else
  docker exec -d $C sh -c 'cd /src && rm -rf /data/vision-build && mkdir -p /data/vision && (cmake -S tools/vision -B /data/vision-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLAMA_DIR=third_party/llama.cpp > /data/_vision_build.log 2>&1 && cmake --build /data/vision-build --target strata-vision -j8 >> /data/_vision_build.log 2>&1 && cp /data/vision-build/bin/strata-vision /data/vision/ && echo VISION_BUILD_OK >> /data/_vision_build.log) || echo VISION_BUILD_FAIL >> /data/_vision_build.log'
  sleep 10
  echo "--- 日志尾部 ---"; tail -c 600 "/home/albus/strata166/data/_vision_build.log" 2>/dev/null || echo "(暂无)"
fi
echo
echo "===== 2) pack 生成进度 ====="
tail -c 600 /home/albus/strata166/data/_iqpack_huihui.log 2>/dev/null || echo "(暂无日志)"
echo "--- 产物 ---"; ls -l /home/albus/strata166/data/packs/huihui-ud-iq4_xs/ 2>/dev/null
echo
echo "===== 3) runconfig.py 的 SPEC 表（找 vision 键定义）====="
docker exec $C sh -c 'grep -n "SPEC" /src/serve/runconfig.py | head -20'
echo "---"
docker exec $C sh -c 'sed -n "1,85p" /src/serve/runconfig.py'
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=900)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_vision_kick.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
