#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, base64
REMOTE = "albus@192.168.50.166"
INNER = r'''
set -u
O=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda/router_top10.cu.o
ls -l "$O"
echo "=== bundler list ==="
/opt/rocm/llvm/bin/clang-offload-bundler --list --type=o --input="$O" 2>&1 | head -5
echo "=== sections ==="
/opt/rocm/llvm/bin/llvm-readobj --sections "$O" 2>&1 | grep -E "Name:" | head -20
echo "=== file type ==="
/opt/rocm/llvm/bin/llvm-readobj --file-headers "$O" 2>&1 | grep -E "Format|Arch|Machine" | head -5
'''
b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(p.stdout.decode("utf-8","replace")[:3000])
