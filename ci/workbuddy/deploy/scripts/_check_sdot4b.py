# -*- coding: utf-8 -*-
"""自证式反汇编检查：先证明 objdump 有输出，再统计 v_dot4_i32_i8。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
docker exec strata166-401 bash -lc '
set +e
OBJ=/src/build-906/CMakeFiles/strata_mmq.dir/third_party/llama.cpp/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu.o
OD=/opt/rocm/llvm/bin/llvm-objdump
echo "=== obj 架构信息 ==="
/opt/rocm/llvm/bin/llvm-readelf -h "$OBJ" 2>/dev/null | head -12
echo
echo "=== 反汇编（不加 --arch-name，读对象自身 arch）==="
$OD -d "$OBJ" > /tmp/d.txt 2>/tmp/d.err
echo "rc=$?  行数=$(wc -l < /tmp/d.txt)  err=$(cat /tmp/d.err | head -2)"
echo "--- 前 15 行 ---"
head -15 /tmp/d.txt
echo
echo "=== 统计（仅在反汇编非空时可信）==="
for pat in v_dot4_i32_i8 v_dot4 sdot4 v_mad_i32 v_perm_b32 v_bfe_u32 v_bfe_i32 v_lshlrev; do
  echo "  $(grep -c "$pat" /tmp/d.txt)  $pat"
done
echo
echo "=== 若非 0，给一条样例 ==="
grep -m3 "v_dot4" /tmp/d.txt
'
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=600)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:400])
