#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, base64
REMOTE = "albus@192.168.50.166"
INNER = r'''
set +e
COB=/opt/rocm/llvm/bin/clang-offload-bundler
OC=/opt/rocm/llvm/bin/llvm-objcopy
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
f=router_top10
cd /tmp; rm -f $f.fat $f.hsaco
$OC --dump-section .hip_fatbin=/tmp/$f.fat $D/$f.cu.o 2>/dev/null
ID=$($COB --list --type=o --input=/tmp/$f.fat | grep -m1 amdgcn)
$COB --unbundle --type=o --targets=$ID --input=/tmp/$f.fat --output=/tmp/$f.hsaco 2>/dev/null
echo "id=$ID size=$(stat -c%s /tmp/$f.hsaco)"
/opt/rocm/llvm/bin/llvm-readobj --notes /tmp/$f.hsaco 2>&1 | head -60
'''
b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(p.stdout.decode("utf-8","replace")[:4000])
