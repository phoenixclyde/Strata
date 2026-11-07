# B6 续：读 il_arch_ok() / g_multi_exact / #if 条件；并读 final_bench.py 了解现成基准
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
C=strata166-407
echo "===== A) native_mmvq.cu 2560-2660（含 #if/#else 边界）====="
docker exec $C sh -c 'sed -n "2555,2660p" /src/src/kernels/cuda/native_mmvq.cu'
echo
echo "===== B) il_arch_ok 定义 ====="
docker exec $C sh -c 'grep -rn -B4 -A14 "il_arch_ok" /src/src/kernels/cuda/native_mmvq.cu | head -60'
echo
echo "===== C) g_multi_exact 定义 ====="
docker exec $C sh -c 'grep -rn -B3 -A10 "g_multi_exact" /src/src/kernels/cuda/*.cu /src/src/kernels/cuda/*.cuh 2>/dev/null | head -40'
echo
echo "===== D) il_cc() 与 il_rows 的默认表 ====="
docker exec $C sh -c 'grep -rn -B3 -A18 "int il_cc" /src/src/kernels/cuda/native_mmvq.cu | head -40'
echo
echo "===== E) 该文件的 #if 顶部（架构门槛）====="
docker exec $C sh -c 'grep -n "^#if\|^#else\|^#endif\|^#ifdef\|^#ifndef" /src/src/kernels/cuda/native_mmvq.cu | head -20'
echo
echo "===== F) final_bench.py 全文 ====="
head -80 /home/albus/strata166/data/final_bench.py
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w716_b6b.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
