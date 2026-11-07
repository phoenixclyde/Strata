#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐内核资源探测：每个文件单独一次探针（上一个循环在第二个文件处静默中断，改为单文件调用定位）。"""
import subprocess, base64, sys

REMOTE = "albus@192.168.50.166"

INNER_T = r'''
set +e
COB=/opt/rocm/llvm/bin/clang-offload-bundler
RO=/opt/rocm/llvm/bin/llvm-readobj
OC=/opt/rocm/llvm/bin/llvm-objcopy
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
f=__F__
O=$D/$f.cu.o
cd /tmp
rm -f /tmp/$f.fat /tmp/$f.hsaco
$OC --dump-section .hip_fatbin=/tmp/$f.fat "$O" 2>/dev/null
if [ ! -s /tmp/$f.fat ]; then echo "NODEV $f"; exit 0; fi
ID=$($COB --list --type=o --input=/tmp/$f.fat 2>/dev/null | grep -m1 amdgcn)
if [ -z "$ID" ]; then echo "NOID $f"; exit 0; fi
$COB --unbundle --type=o --targets=$ID --input=/tmp/$f.fat --output=/tmp/$f.hsaco 2>/dev/null
if [ ! -s /tmp/$f.hsaco ]; then echo "UNBUNDLEFAIL $f ($ID)"; exit 0; fi
echo "OK $f"
$RO --notes /tmp/$f.hsaco 2>/dev/null | awk -v S="$f" '
  /Name: /{k=$2}
  /NumVgprs:/{v=$2}
  /NumSgprs:/{s=$2}
  /PrivateSegmentSize:/{p=$2}
  /GroupSegmentFixedSize:/{g=$2}
  /WavefrontSize:/{w=$2; if (k ~ /kernel/) printf "%-46s vgpr=%-4s sgpr=%-3s priv=%-7s lds=%-6s wave=%-2s src=%s\n", k,v,s,p,g,w,S}
'
'''

def probe(name):
    inner = INNER_T.replace("__F__", name)
    b = base64.b64encode(inner.encode()).decode()
    outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
    p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"],
                       input=base64.b64encode(outer.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    return p.stdout.decode("utf-8","replace").strip()

for n in sys.argv[1:]:
    print("#### " + n)
    print(probe(n))
