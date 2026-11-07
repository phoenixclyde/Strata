#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找出 prompt attention 内核实际编译进哪个目标文件；并确认它在最终二进制里存在。"""
import subprocess, base64
REMOTE = "albus@192.168.50.166"
INNER = r'''
set +e
echo "=== 哪些 .o 含 prompt_attn_i8v3 ==="
grep -rl --binary-files=text "prompt_attn_i8v3" /src/build-906 2>/dev/null | head -8
echo "=== 哪些 .o 含 prompt_attn_kernel ==="
grep -rl --binary-files=text "prompt_attn_kernel" /src/build-906 2>/dev/null | head -8
echo "=== 最终二进制 ==="
grep -c --binary-files=text "prompt_attn_i8v3" /src/build-906/strata 2>/dev/null
echo "=== 源文件里是否被 #if 排除 ==="
grep -n "STRATA_HIP_GFX906\|__HIPCC__\|#if 0\|#endif" /src/src/kernels/cuda/qsa_prompt_attn.cu | head -12
echo "=== 该 TU 的编译单元大小 ==="
ls -l /src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_prompt_attn.cu.o
grep -c "" /src/src/kernels/cuda/qsa_prompt_attn.cu
'''
b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
print(p.stdout.decode("utf-8","replace")[:3000])
