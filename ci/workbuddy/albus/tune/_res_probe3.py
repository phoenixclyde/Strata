#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 .hip_fatbin 抽出 device code object 并读 amdhsa 元数据（VGPR/SGPR/私有段）。"""
import subprocess, base64
REMOTE = "albus@192.168.50.166"

INNER = r'''
set -u
COB=/opt/rocm/llvm/bin/clang-offload-bundler
RO=/opt/rocm/llvm/bin/llvm-readobj
OC=/opt/rocm/llvm/bin/llvm-objcopy
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
mkdir -p /tmp/res; cd /tmp/res
for f in qsa_prompt_attn qsa_decode_attn qsa native_mmvq s2_expert_grouped router_top10 s_gemv iq_kernels verify_kernels; do
  O="$D/$f.cu.o"
  [ -f "$O" ] || { echo "MISS $f"; continue; }
  $OC --dump-section .hip_fatbin="$f.fat" "$O" >/dev/null 2>&1 || { echo "DUMPFAIL $f"; continue; }
  [ -s "$f.fat" ] || { echo "EMPTYFAT $f"; continue; }
  ID=$( $COB --list --type=o --input="$f.fat" 2>/dev/null | grep -m1 amdgcn )
  if [ -n "$ID" ]; then
    $COB --unbundle --type=o --targets="$ID" --input="$f.fat" --output="$f.hsaco" 2>/dev/null || { echo "UNBUNDLEFAIL $f"; continue; }
    HS="$f.hsaco"
  else
    HS="$f.fat"
  fi
  $RO --notes "$HS" 2>/dev/null | awk -v S="$f" '
    /Name: /{k=$2}
    /NumVgprs:/{v=$2}
    /NumSgprs:/{s=$2}
    /PrivateSegmentSize:/{p=$2}
    /GroupSegmentFixedSize:/{g=$2}
    /WavefrontSize:/{w=$2; printf "%-50s vgpr=%-4s sgpr=%-3s priv=%-7s lds=%-6s wave=%-2s src=%s\n", k,v,s,p,g,w,S}
  '
done
'''

b = base64.b64encode(INNER.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
o = p.stdout.decode("utf-8","replace")
print("lines:", len(o.splitlines()))
print(o[:6000])
