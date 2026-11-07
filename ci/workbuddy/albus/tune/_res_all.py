#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性在 166 容器内：抽 .hip_fatbin -> unbundle gfx906 -> 读 amdhsa 元数据（VGPR/SGPR/私有段）。"""
import subprocess, base64
REMOTE = "albus@192.168.50.166"

INNER = r'''
set +e
COB=/opt/rocm/llvm/bin/clang-offload-bundler
RO=/opt/rocm/llvm/bin/llvm-readobj
OC=/opt/rocm/llvm/bin/llvm-objcopy
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
cd /tmp
for f in qsa_prompt_attn qsa_decode_attn qsa native_mmvq s2_expert_grouped router_top10 s_gemv iq_kernels verify_kernels sampler; do
  O="$D/$f.cu.o"
  if [ ! -f "$O" ]; then echo "MISS $f"; continue; fi
  $OC --dump-section .hip_fatbin=/tmp/$f.fat "$O" >/dev/null 2>&1
  if [ ! -s /tmp/$f.fat ]; then echo "NODEV $f"; continue; fi
  ID=$($COB --list --type=o --input=/tmp/$f.fat 2>/dev/null | grep -m1 amdgcn)
  if [ -z "$ID" ]; then echo "NOID $f"; continue; fi
  $COB --unbundle --type=o --targets=$ID --input=/tmp/$f.fat --output=/tmp/$f.hsaco >/dev/null 2>&1
  if [ ! -s /tmp/$f.hsaco ]; then echo "UNBUNDLEFAIL $f"; continue; fi
  $RO --notes /tmp/$f.hsaco 2>/dev/null | awk -v S="$f" '
    /Name: /{k=$2}
    /NumVgprs:/{v=$2}
    /NumSgprs:/{s=$2}
    /PrivateSegmentSize:/{p=$2}
    /GroupSegmentFixedSize:/{g=$2}
    /WavefrontSize:/{w=$2; if (k ~ /kernel|attn|mmvq|moe|gemv|router|sampler/) printf "%-48s vgpr=%-4s sgpr=%-3s priv=%-7s lds=%-6s wave=%-2s src=%s\n", k,v,s,p,g,w,S}
  '
done
'''

b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
o = p.stdout.decode("utf-8","replace")
lines = [l for l in o.splitlines() if l.strip()]
print("KERNELS:", len(lines))
print("\n".join(lines))
