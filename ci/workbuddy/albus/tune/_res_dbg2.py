#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, base64
REMOTE = "albus@192.168.50.166"
INNER = r'''
set +e
echo "=== objcopy? ==="
ls -l /opt/rocm/llvm/bin/llvm-objcopy 2>&1 | head -2
echo "=== compile_commands ==="
ls -l /src/build-906/compile_commands.json 2>&1 | head -2
echo "=== flags.make ==="
ls /src/build-906/CMakeFiles/strata_kernels.dir/ | head -6
echo "--- flags ---"
head -c 1200 /src/build-906/CMakeFiles/strata_kernels.dir/flags.make 2>/dev/null
echo
echo "=== 试直接 dump 一节 ==="
O=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda/router_top10.cu.o
/opt/rocm/llvm/bin/llvm-objcopy --dump-section .hip_fatbin=/tmp/x.fat "$O" 2>&1 | head -3
ls -l /tmp/x.fat 2>&1 | head -2
'''
b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(p.stdout.decode("utf-8","replace")[:3000])
