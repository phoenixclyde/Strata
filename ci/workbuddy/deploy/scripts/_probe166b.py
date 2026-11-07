# -*- coding: utf-8 -*-
"""166 第二轮只读探针：构建环境（镜像里有啥）+ 已有 gguf + pip 源 + 磁盘占用大户。"""
import base64, os, shutil, subprocess, time

HOST = '192.168.50.166'
USER = 'albus'
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
OUT = r'D:\workbuddy_space\2026-10-04-13-25-07\_166_probe2.txt'

SCRIPT = r'''
set +e
echo "=== routek-base 镜像内容（cmake/ninja/clang/hipcc/rocm 版本）==="
BASE=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep '^routek-base:gfx906-rocm101-hip716-torch215$' | head -1)
echo "image=$BASE"
docker run --rm --entrypoint bash "$BASE" -lc '
  echo "--- os ---"; (. /etc/os-release; echo "$PRETTY_NAME")
  echo "--- tools ---"; for c in cmake ninja clang clang++ hipcc gcc g++ git python3 pip3; do printf "  %-10s " $c; command -v $c || echo MISSING; done
  echo "--- rocm ---"; ls -d /opt/rocm* 2>&1; cat /opt/rocm/.info/version 2>/dev/null; ls /opt/rocm/lib/libamdhip64* /opt/rocm/lib/libhipblas* 2>&1 | head
  echo "--- rocm target libs ---"; ls /opt/rocm/lib/llvm/lib/clang/*/lib/*/ 2>/dev/null | head -3
  echo "--- python ---"; python3 -c "import sys;print(sys.version)" 2>&1; python3 -c "import numpy;print(\"numpy\",numpy.__version__)" 2>&1
  echo "--- cmake version ---"; cmake --version 2>&1 | head -1
  echo "--- ninja ---"; ninja --version 2>&1 | head -1
' 2>&1 | sed 's/^/  /'
echo
echo "=== mixa3607 相关镜像 / 可拉性 ==="
docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}' | grep -i mixa 2>&1
cat /etc/docker/daemon.json 2>&1
echo "--- 试探 manifest（只查不拉）---"
timeout 60 docker manifest inspect mixa3607/rocm-gfx906:7.14-complete 2>&1 | head -8
echo "rc=$?"
echo
echo "=== 已有 gguf / 模型文件（>100MB）==="
find / -xdev -type f -size +100M \( -name '*.gguf' -o -name '*.safetensors' -o -name '*.bin' \) -printf '%s\t%p\n' 2>/dev/null | sort -rn | head -30 | awk -F'\t' '{printf "  %8.2f GB  %s\n", $1/1e9, $2}'
echo
echo "=== pip 源 / 网络代理 ==="
cat /etc/pip.conf ~/.pip/pip.conf ~/.config/pip/pip.conf 2>&1 | head -20
env | grep -iE 'proxy|PIP_INDEX|HF_ENDPOINT|MODELSCOPE' 2>&1
echo "--- pip 探测 ---"
timeout 40 python3 -m pip download --no-deps -d /tmp/_pipprobe numpy 2>&1 | tail -5
rm -rf /tmp/_pipprobe
echo
echo "=== 磁盘大户 ==="
df -h / | tail -1
sudo du -x -h -d 1 /home /var /opt /root 2>/dev/null | sort -h | tail -25
echo
echo "=== /home/albus 一览 ==="
ls -la /home/albus | head -30
echo
echo "=== rocminfo 认卡 ==="
timeout 60 rocminfo 2>&1 | grep -E 'Name:|gfx|Marketing|Compute Unit|Wavefront|Cache Info|Chip ID' | head -25
echo
echo "=== ROCm 版本（系统）==="
cat /opt/rocm/.info/version 2>&1 | head -3
/opt/rocm/bin/hipcc --version 2>&1 | head -5
echo
echo "=== 内核模块参数生效值 ==="
for f in vm_update_mode noretry; do printf '  amdgpu.%s = ' $f; cat /sys/module/amdgpu/parameters/$f 2>&1; done
echo "  iommu: $(cat /proc/cmdline)"
echo
echo "=== 现有容器 ==="
docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>&1
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY,
       '%s@%s' % (USER, HOST), 'base64 -d | bash']

t0 = time.time()
try:
    p = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
    out, err, rc = p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace'), p.returncode
except subprocess.TimeoutExpired as e:
    out = (e.stdout or b'').decode('utf-8', 'replace')
    err, rc = 'TIMEOUT', -1

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('rc=%s  %.1fs\n%s\n--- STDERR ---\n%s\n' % (rc, time.time() - t0, out, err))
print('rc=%s  %.1fs -> %s' % (rc, time.time() - t0, OUT))
print(out[:4000])
print('--- ERR ---')
print(err[:600])
