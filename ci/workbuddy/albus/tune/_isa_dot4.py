#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 166 上反汇编关键内核，统计 v_dot4（硬件 dp4a）与标量模拟指令的出现次数。
判据：若 Strata 自有内核里 v_dot4 = 0 而 v_mul_i32_i24/v_lshr 很多 => STRATA_DP4A 在 gfx906 走了标量分支。"""
import subprocess, base64

REMOTE = "albus@192.168.50.166"

INNER = r'''
set +e
COB=/opt/rocm/llvm/bin/clang-offload-bundler
OC=/opt/rocm/llvm/bin/llvm-objcopy
OD=/opt/rocm/llvm/bin/llvm-objdump
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
cd /tmp
printf "%-18s %8s %8s %8s %8s %8s\n" TU dot4 dot2 mul_i24 lshr v_perm
for f in native_mmvq iq_kernels qsa_decode_attn qsa s2_expert_grouped fused_gr router_top10 dflash2; do
  O=$D/$f.cu.o
  [ -f "$O" ] || { echo "MISS $f"; continue; }
  rm -f /tmp/$f.fat /tmp/$f.hsaco /tmp/$f.s
  $OC --dump-section .hip_fatbin=/tmp/$f.fat "$O" 2>/dev/null
  [ -s /tmp/$f.fat ] || { echo "NODEV $f"; continue; }
  ID=$($COB --list --type=o --input=/tmp/$f.fat 2>/dev/null | grep -m1 amdgcn)
  [ -n "$ID" ] || { echo "NOID $f"; continue; }
  $COB --unbundle --type=o --targets=$ID --input=/tmp/$f.fat --output=/tmp/$f.hsaco 2>/dev/null
  $OD -d --mcpu=gfx906 /tmp/$f.hsaco > /tmp/$f.s 2>/dev/null
  d4=$(grep -c "v_dot4" /tmp/$f.s)
  d2=$(grep -c "v_dot2" /tmp/$f.s)
  m24=$(grep -c "v_mul_i32_i24" /tmp/$f.s)
  shr=$(grep -c "v_lshrrev_b32" /tmp/$f.s)
  prm=$(grep -c "v_perm_b32" /tmp/$f.s)
  printf "%-18s %8s %8s %8s %8s %8s\n" "$f" "$d4" "$d2" "$m24" "$shr" "$prm"
done
echo "--- 对照：vendored llama.cpp 的 mmq 目标文件（若存在）---"
find /src/build-906 -name "mmq.cu.o" 2>/dev/null | head -3
'''

b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
print(p.stdout.decode("utf-8","replace")[:4000])
