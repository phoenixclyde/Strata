# 166 现状快照：容器 / config / metrics / 主机资源
import subprocess, base64, sys

HOST = "albus@192.168.50.166"

SH = r'''
set +e
echo "===DOCKER==="
docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}' | head -20
echo "===INSPECT_ENV==="
docker inspect strata166-407 --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | sort
echo "===INSPECT_CMD==="
docker inspect strata166-407 --format '{{json .Config.Cmd}}' 2>/dev/null
echo "===INSPECT_HOSTCFG==="
docker inspect strata166-407 --format '{{json .HostConfig.Ulimits}} {{json .HostConfig.IpcMode}} {{json .HostConfig.ShmSize}}' 2>/dev/null
echo "===ENGINEVER==="
docker exec strata166-407 /src/build-906/strata --version 2>&1 | head -3
echo "===METRICS==="
curl -s --max-time 5 http://127.0.0.1:8090/metrics
echo ""
echo "===HEALTH==="
curl -s --max-time 5 http://127.0.0.1:8090/health
echo ""
echo "===HOST==="
free -m
echo "---nproc---"
nproc
echo "---gov---"
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver 2>/dev/null
echo "---thp---"
cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null
cat /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null
echo "---hugepages---"
grep -E "HugePages_|Hugepagesize" /proc/meminfo
echo "---ulimit---"
ulimit -l
echo "---loadavg---"
cat /proc/loadavg
echo "---meminfo_extra---"
grep -E "^(MemTotal|MemFree|MemAvailable|Cached|Shmem|Dirty|Writeback|AnonPages|Mapped|Unevictable)" /proc/meminfo
echo "===GPUSYS==="
/opt/rocm/bin/rocm-smi --showuse --showmemuse --showpower --showtemp 2>&1 | head -40
echo "===LINKSPEED==="
/opt/rocm/bin/rocm-smi --showbus 2>&1 | head -20
echo "===PS==="
docker exec strata166-407 ps -o pid,pcpu,rss,nlwp,comm -p 1 2>&1 | head -5
echo "===NODEINFO==="
lscpu | grep -E "^(Model name|CPU\(s\)|Thread|Core|Socket|NUMA node|L3)"
ls /sys/devices/system/node/ | grep node
'''

b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, "base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out = p.stdout.decode("utf-8", "replace")
err = p.stderr.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/albus/tune/_probe166.out.txt", "w", encoding="utf-8").write(out)
print("RC", p.returncode, "len", len(out))
print("STDERR:", err[:500])
print(out[:9000])
