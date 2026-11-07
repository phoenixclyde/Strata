#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, base64
REMOTE = "albus@192.168.50.166"
INNER = r'''
set +e
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
for f in qsa_prompt_attn qsa_decode_attn native_mmvq s2_expert_grouped router_top10; do
  O=$D/$f.cu.o
  sz=$(stat -c%s "$O" 2>/dev/null)
  has=$(/opt/rocm/llvm/bin/llvm-readobj --sections "$O" 2>/dev/null | grep -c "hip_fatbin")
  echo "$f size=$sz fatbin_sections=$has"
done
echo "--- obj dir listing ---"
ls -l $D | head -8
'''
b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(p.stdout.decode("utf-8","replace")[:2000])
