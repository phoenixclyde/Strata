#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, base64
REMOTE = "albus@192.168.50.166"
INNER = r'''
set +e
F=/tmp/x.fat
echo "=== head of fat ==="
head -c 32 $F | od -c | head -3
echo "=== bundler list ==="
/opt/rocm/llvm/bin/clang-offload-bundler --list --type=o --input=$F 2>&1 | head -5
echo "=== readobj notes directly ==="
/opt/rocm/llvm/bin/llvm-readobj --notes $F 2>&1 | head -30
'''
b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(p.stdout.decode("utf-8","replace")[:3000])
