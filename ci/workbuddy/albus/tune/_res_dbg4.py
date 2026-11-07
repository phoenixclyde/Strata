#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, base64
REMOTE = "albus@192.168.50.166"
INNER = r'''
set +e
O=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda/router_top10.cu.o
cd /tmp
/opt/rocm/llvm/bin/llvm-objcopy --dump-section .hip_fatbin=/tmp/x.fat "$O"; echo "dump rc=$?"
ls -l /tmp/x.fat
echo "=== bundler list ==="
/opt/rocm/llvm/bin/clang-offload-bundler --list --type=o --input=/tmp/x.fat; echo "list rc=$?"
echo "=== notes ==="
/opt/rocm/llvm/bin/llvm-readobj --notes /tmp/x.fat 2>&1 | head -40
'''
b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(p.stdout.decode("utf-8","replace")[:4000])
