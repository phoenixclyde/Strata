# -*- coding: utf-8 -*-
"""实测 166（gfx906 测试台）配置：只读探针，base64 走 ssh，输出落文件。"""
import base64, os, shutil, subprocess, sys, time

HOST = '192.168.50.166'
USER = 'albus'
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
BIN_CANDS = [r'C:\Program Files\Git\usr\bin\ssh.exe',
             r'C:\Program Files\Git\bin\ssh.exe',
             shutil.which('ssh')]
SSH = next((p for p in BIN_CANDS if p and os.path.exists(p)), None)
OUT = r'D:\workbuddy_space\2026-10-04-13-25-07\_166_probe.txt'

SCRIPT = r'''
set +e
echo "=== ID ==="
hostname
uptime -s; uptime
( . /etc/os-release; echo "$PRETTY_NAME  kernel=$(uname -r)" )
cat /proc/sys/kernel/random/boot_id
echo
echo "=== CPU ==="
lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core\(s\)|Socket|NUMA node\(s\)|MHz|Cache'
FL=$(grep -m1 '^flags' /proc/cpuinfo)
for f in avx avx2 avx512f avx512bw avx512vl avx512_vnni avx512vbmi fma f16c bmi2; do
  case " $FL " in *" $f "*) echo "  $f=1";; *) echo "  $f=0";; esac
done
echo
echo "=== RAM ==="
free -m
grep -E 'MemTotal|MemAvailable|SwapTotal' /proc/meminfo
echo
echo "=== GPU (lspci 全部) ==="
lspci -nn | grep -Ei 'vga|display|3d|accelerator'
echo
echo "=== GPU 设备节点 ==="
ls -l /dev/kfd /dev/dri 2>&1
echo
echo "=== KFD 拓扑 ==="
for n in /sys/class/kfd/kfd/topology/nodes/*; do
  [ -d "$n" ] || continue
  echo "-- node $(basename $n): cpu_cores=$(cat $n/cpu_cores_per_unit 2>/dev/null) gpu_id=$(cat $n/properties 2>/dev/null | grep -m1 'gpu_id' )"
  grep -E '^(gfx_target_version|simd_count|name|device_id|vendor_id)' $n/properties 2>/dev/null | tr '\n' ' '
  echo
done
echo
echo "=== ROCm / rocm-smi ==="
ls -d /opt/rocm* 2>&1
( /opt/rocm/bin/rocm-smi --showmeminfo vram 2>&1 | head -30 ) || echo "no rocm-smi"
which rocm-smi rocminfo hipcc 2>&1
echo
echo "=== amdgpu 驱动 ==="
modinfo amdgpu 2>&1 | grep -E '^version|^filename|^srcversion'
ls /etc/modprobe.d/ 2>&1
grep -rEh 'amdgpu|kfd|iommu' /etc/modprobe.d/ 2>&1 | head -20
cat /proc/cmdline
echo
echo "=== 磁盘 ==="
df -h / /home /var 2>&1 | head -12
lsblk -d -o NAME,SIZE,ROTA,MODEL 2>&1
echo
echo "=== BAR / 链路 ==="
for s in $(lspci -nn | grep -Ei 'vga|display|3d|accelerator' | awk '{print $1}'); do
  echo "-- slot $s"
  lspci -vv -s $s 2>&1 | grep -E 'Region [0246]:|LnkSta:|LnkCap:' | head -8
done
echo
echo "=== 工具链 ==="
for c in gcc g++ cmake ninja clang clang++ python3 git git-lfs curl docker; do
  printf '  %-10s ' $c; command -v $c || echo MISSING
done
python3 -c "import sys;print('  python', sys.version.split()[0])" 2>&1
echo
echo "=== docker ==="
docker --version 2>&1
docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}' 2>&1 | head -20
echo
echo "=== 网络（目标机自己能不能下）==="
for u in https://www.modelscope.cn https://huggingface.co https://hf-mirror.com https://github.com; do
  printf '  %-30s ' $u
  curl -s -o /dev/null -m 8 -w '%{http_code} %{time_total}s\n' $u || echo FAIL
done
echo
echo "=== 现有进程 / 服务 ==="
ps aux | grep -Ei 'vllm|strata|llama|python' | grep -v grep | head -15
ss -lntp 2>/dev/null | head -20
echo
echo "=== 已有 Strata / 相关目录 ==="
ls -d ~/Strata* /opt/Strata* /data/Strata* 2>&1 | head
df -h /mnt /data 2>&1 | head -8
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
       '-i', KEY, '%s@%s' % (USER, HOST), 'base64 -d | bash']

t0 = time.time()
try:
    p = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=180)
    out = p.stdout.decode('utf-8', 'replace')
    err = p.stderr.decode('utf-8', 'replace')
    rc = p.returncode
except subprocess.TimeoutExpired as e:
    out = (e.stdout or b'').decode('utf-8', 'replace')
    err = 'TIMEOUT'
    rc = -1

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('SSH=%s\nTIMEOUT/rc=%s  %.1fs\n%s\n--- STDERR ---\n%s\n' % (SSH, rc, time.time() - t0, out, err))
print('rc=%s  %.1fs  -> %s' % (rc, time.time() - t0, OUT))
print(out[:1500])
print('--- ERR ---')
print(err[:800])
