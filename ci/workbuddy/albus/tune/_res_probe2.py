#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 166 上解出每内核 VGPR/SGPR/私有段（溢出足迹）。方法：内层脚本 base64 传入容器，避免嵌套引号。"""
import subprocess, base64

REMOTE = "albus@192.168.50.166"

INNER = r'''
set -u
COB=/opt/rocm/llvm/bin/clang-offload-bundler
RO=/opt/rocm/llvm/bin/llvm-readobj
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
mkdir -p /tmp/res; cd /tmp/res
for f in qsa_prompt_attn qsa_decode_attn qsa native_mmvq s2_expert_grouped router_top10 s_gemv verify_kernels iq_kernels; do
  O="$D/$f.cu.o"
  if [ ! -f "$O" ]; then echo "MISS $f"; continue; fi
  ID=$( $COB --list --type=o --input="$O" 2>/dev/null | grep -m1 amdgcn )
  if [ -z "$ID" ]; then echo "NOBUNDLE $f"; continue; fi
  if ! $COB --unbundle --type=o --targets="$ID" --input="$O" --output="$f.hsaco" 2>/dev/null; then echo "UNBUNDLE_FAIL $f ($ID)"; continue; fi
  $RO --notes "$f.hsaco" 2>/dev/null | awk -v F="$f" '
    /Name: /{k=$2}
    /NumVgprs:/{v=$2}
    /NumSgprs:/{s=$2}
    /PrivateSegmentSize:/{p=$2}
    /GroupSegmentFixedSize:/{g=$2}
    /ScratchSize:/{sc=$2}
    /WavefrontSize:/{w=$2; printf "%-52s vgpr=%-4s sgpr=%-4s priv=%-6s lds=%-6s scratch=%-4s wave=%-2s src=%s\n", k,v,s,p,g,sc,w,F}
  '
done
'''

outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1'

def run(script):
    b = base64.b64encode(script.encode()).decode()
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", REMOTE, "base64 -d | bash"],
                       input=base64.b64encode((outer % b).encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    return p.stdout.decode("utf-8", "replace")

out = run(INNER)
lines = [l for l in out.splitlines() if l.strip()]
print("lines:", len(lines))
for l in lines:
    print(l)
