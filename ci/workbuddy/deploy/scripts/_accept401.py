# -*- coding: utf-8 -*-
"""验收 strata-gfx906:0.1.40.1：版本、开关、以及关键 —— Q6_K 的 mul_mat_q_case 符号是否落地。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
set +e
IMG=strata-gfx906:0.1.40.1
echo "=== 镜像 ==="
docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}' | grep -i strata
echo
echo "=== 版本 / 可执行 ==="
docker run --rm --entrypoint bash $IMG -lc '
  ls -l /src/build-906/strata
  /src/build-906/strata --version 2>&1 | head -3 || true
  echo "--- help head ---"
  /src/build-906/strata --help 2>&1 | head -4
'
echo
echo "=== CMake 开关 ==="
docker run --rm --entrypoint bash $IMG -lc '
  grep -E "^STRATA_(ENABLE_CUDA|ENABLE_HIP|HIP_GFX906|MMQ_KQUANTS|Q6K_EXPERTS|ORCA_Q4KS_MMQ|PREFILL_MMQ):" /src/build-906/CMakeCache.txt
  echo "--- mmq 实例源文件（build.ninja 里的 template-instances）---"
  grep -o "template-instances/mmq-instance-[a-z0-9_]*\.cu" /src/build-906/build.ninja | sort -u
'
echo
echo "=== 关键符号：mul_mat_q_case 的全部实例（<14> 就是 Q6_K）==="
docker run --rm --entrypoint bash $IMG -lc '
  nm -C /src/build-906/strata 2>/dev/null | grep -o "mul_mat_q_case<(ggml_type)[0-9]*>" | sort -u
  echo "--- 计数 ---"
  nm -C /src/build-906/strata 2>/dev/null | grep -c "mul_mat_q_case"
  echo "--- strata_mmq.a 大小 ---"
  ls -l /src/build-906/libstrata_mmq.a
'
echo
echo "=== 补丁复核（H1-H5 目标形态必须都在）==="
docker run --rm --entrypoint bash $IMG -lc '
  grep -n "inline hipError_t cudaFuncSetAttribute" /src/include/strata/platform/hip_compat/strata_hip.h | head -2
  grep -n "no q8_1 either" /src/src/kernels/cuda/fused_gr.cu | head -2
  grep -n "STRATA_HIP_GFX906)   // (HIP and gfx906" /src/src/core/mtp.cpp | head -2
  grep -n "STRATA_HIP_GFX906)$" /src/src/core/vmm.cpp | head -2
  grep -n "STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906" /src/CMakeLists.txt
'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
                    '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- stderr ---')
    print(e[:800])
