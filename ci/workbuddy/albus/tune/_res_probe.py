#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 166 上解出每内核的 VGPR / SGPR / 私有段（溢出足迹），不占 GPU。
方法：clang-offload-bundler --unbundle 取出 gfx906 的 device code object -> llvm-readobj --notes 解析 amdhsa 元数据。"""
import subprocess, base64

REMOTE = "albus@192.168.50.166"

SCRIPT = r'''
set -u
docker run --rm --entrypoint sh strata-gfx906:0.2.3 -c '
set -u
COB=/opt/rocm/llvm/bin/clang-offload-bundler
RO=/opt/rocm/llvm/bin/llvm-readobj
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
mkdir -p /tmp/res && cd /tmp/res
for f in qsa_prompt_attn qsa_decode_attn qsa native_mmvq s2_expert_grouped router_top10 s_gemv verify_kernels; do
  o=$D/$f.cu.o
  [ -f "$o" ] || continue
  id=$($COB --list --type=o --input="$o" 2>/dev/null | grep -m1 "amdgcn" )
  [ -n "$id" ] || { echo "?? $f no device bundle"; continue; }
  $COB --unbundle --type=o --targets="$id" --input="$o" --output="$f.hsaco" 2>/dev/null || { echo "?? $f unbundle failed ($id)"; continue; }
  $RO --notes "$f.hsaco" 2>/dev/null | awk -v F="$f" "
    /Name: /{ k=\$2 }
    /NumVgprs:/{ v=\$2 }
    /NumSgprs:/{ s=\$2 }
    /PrivateSegmentSize:/{ p=\$2 }
    /GroupSegmentFixedSize:/{ g=\$2 }
    /\.private_segment_fixed_size:/{ p=\$2 }
    /\.group_segment_fixed_size:/{ g=\$2 }
    /WavefrontSize:/{ w=\$2; printf \"%-46s vgpr=%-4s sgpr=%-4s priv=%-6s lds=%-6s wave=%s src=%s\n\", k, v, s, p, g, w, F }
  "
done
' 2>&1 | sort -t= -k2 -rn | head -70
'''

p = subprocess.run(["ssh", "-o", "BatchMode=yes", REMOTE, "base64 -d | bash"],
                   input=base64.b64encode(SCRIPT.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
print(p.stdout.decode("utf-8", "replace"))
