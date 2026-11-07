# 166 机器真相：CPU 指令集（AVX2 / AVX-512）+ 引擎日志的 CPU 告警 + 0.1.41 构建状态
import subprocess, base64

REMOTE = """set -u
echo '== CPU 型号 =='
grep -m1 'model name' /proc/cpuinfo
echo '== 逻辑核数 =='
nproc
echo '== 指令集实测（有该 flag 的逻辑核数）=='
for f in avx avx2 fma bmi2 avx512f avx512vl avx512bw avx512vnni; do
  n=$(grep -c " $f " /proc/cpuinfo 2>/dev/null || true)
  [ -z "$n" ] && n=0
  echo "  $f = $n"
done
echo '== 引擎日志里的 CPU / AVX 相关行 =='
grep -iE 'avx|sse|wide instr|cpu pool|no avx' /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -n 8 || echo '(无)'
echo '== 0.1.41 构建状态 =='
pgrep -af 'docker build' | head -1 || echo BUILD_NOT_RUNNING
tail -n 8 /home/albus/strata166/build-ctx-411/build-411.log 2>/dev/null || echo '(无日志)'
echo '== 镜像 =='
docker images --format '{{.Repository}}:{{.Tag}} | {{.Size}}' | grep -i strata
"""

p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(REMOTE.encode("utf-8")) + b"\n",
                   capture_output=True, timeout=180)
print("rc", p.returncode)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-400:])
