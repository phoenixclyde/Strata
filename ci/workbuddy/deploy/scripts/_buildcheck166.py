# -*- coding: utf-8 -*-
"""验证 166 已有 routek-base 镜像能否编出 gfx906（wave64）代码 —— 只读/容器内，不动任何服务。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
OUT = r'D:\workbuddy_space\2026-10-04-13-25-07\_166_buildcheck.txt'

SCRIPT = r'''
set +e
IMG=routek-base:gfx906-rocm101-hip716-torch215
echo "=== 镜像内：clang 实际位置与 hipcc offload 目标 ==="
docker run --rm --entrypoint bash "$IMG" -lc '
  echo "--- /opt/rocm 结构 ---"; ls -d /opt/rocm /opt/rocm/*/ 2>&1 | head -20
  echo "--- llvm 位置 ---"; ls -d /opt/rocm/*/lib/llvm/bin /opt/rocm/llvm/bin 2>&1 | head
  for p in /opt/rocm/llvm/bin/clang++ /opt/rocm/core-7.14/lib/llvm/bin/clang++ /opt/rocm/bin/clang++; do
    printf "  %-46s " $p; [ -x $p ] && echo OK || echo MISSING
  done
  echo "--- hipcc 路径 ---"; cat /opt/rocm/bin/hipcc 2>/dev/null | head -3; which hipcc
  echo "--- nvcc/hcc 无关 ---"
  echo "--- gfx906 是否在 LLVM 目标里 ---"
  CL=$(ls /opt/rocm/*/lib/llvm/bin/clang++ /opt/rocm/llvm/bin/clang++ 2>/dev/null | head -1)
  echo "  clang++ = $CL"
  $CL --print-targets 2>&1 | grep -i amdgcn
  echo "  gfx906 in target list: $($CL -print-targets 2>&1 | grep -c amdgcn)"
  echo "--- 编一个真 kernel 到 gfx906 ---"
  mkdir -p /tmp/_bc && cd /tmp/_bc
  cat > k.hip <<EOF
extern "C" __global__ void k(const float* a, float* b, int n) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) { float s = 0.f; for (int j = 0; j < 8; ++j) s += a[i + j]; b[i] = s; }
}
EOF
  hipcc --offload-arch=gfx906 -O2 -c k.hip -o k.o 2>&1 | tail -20
  echo "  hipcc rc=$?"
  ls -l k.o 2>&1
  echo "--- 抽 .hsaco 看 ISA ---"
  $CL -x hip --offload-arch=gfx906 -O2 --cuda-device-only -c k.hip -o k.hsaco 2>&1 | tail -10
  echo "  clang rc=$?"; ls -l k.hsaco 2>&1
  file k.hsaco 2>&1
  echo "--- 反汇编确认 wave64 指令 ---"
  $CL -x hip --offload-arch=gfx906 --cuda-device-only -S k.hip -o k.s 2>&1 | tail -5
  grep -m5 -E "s_add_f32|s_load_dword|v_add_f32" k.s 2>&1
  echo "--- rocminfo（容器内能否认卡，需 --device）---"
  echo "(本节跳过：本容器未挂 /dev/kfd)"
' 2>&1 | sed 's/^/  /'
echo
echo "=== 宿主上：Strata 构建所需 Python 依赖可达性（清华源）==="
for p in numpy jinja2 regex pyyaml tqdm requests pillow psutil cmake ninja; do
  printf '  %-10s ' $p
  timeout 25 python3 -m pip index versions $p 2>&1 | head -1
done
echo
echo "=== 宿主：/models 挂载点与剩余空间（放权重的候选位置）==="
df -h /models /home / 2>&1
mount | grep -E ' /models | /home ' 2>&1
ls -d /models/* 2>&1 | head -20
echo
echo "=== 宿主：内网互通性（本机 192.168.50.x 能否被 166 反连）==="
ip -4 addr show | grep -E 'inet ' | head
echo "--- 到本机 Windows 的连通性 ---"
for h in 192.168.50.220 192.168.50.1; do printf '  %-16s ' $h; timeout 4 bash -c "echo > /dev/tcp/$h/22" 2>&1 && echo "22 open" || echo "22 closed/no"; done
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY,
       'albus@192.168.50.166', 'base64 -d | bash']
t0 = time.time()
try:
    p = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
    out, err, rc = p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace'), p.returncode
except subprocess.TimeoutExpired as e:
    out, err, rc = (e.stdout or b'').decode('utf-8', 'replace'), 'TIMEOUT', -1

open(OUT, 'w', encoding='utf-8').write('rc=%s %.1fs\n%s\n--- STDERR ---\n%s\n' % (rc, time.time() - t0, out, err))
print('rc=%s %.1fs -> %s' % (rc, time.time() - t0, OUT))
print(out[:5000])
