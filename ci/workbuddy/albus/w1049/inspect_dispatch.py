#!/usr/bin/env python3
# W1049: is the production OPT dispatch (DP4A score) actually reached under TUNED=1 swizzle?
import subprocess

R = "/home/albus/strata166/pr/k10"
PROD = "03509d1b6895b4015f03a3aa416c962e5bf56d3d"  # hc4b build sha (live)


def sh(cmd):
    r = subprocess.run(["bash", "-lc", cmd], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.stdout


print("=== 1. production-sha qsa_decode_attn.cu: gfx906_attn_opt / OPT_DISPATCH / use_query_swizzle context ===")
print(sh("grep -n 'gfx906_attn_opt\\|STRATA_ATTN_OPT_DISPATCH\\|use_query_swizzle\\|query_swizzle_gfx906\\|STRATA_ATTN_CHUNK_SEL' %s/src/kernels/cuda/qsa_decode_attn.cu | head -40" % R))
# also show the actual dispatch block at prod sha via git show
print("=== 2. same, but read from PROD sha object (not worktree) ===")
print(sh("git -C %s show %s:src/kernels/cuda/qsa_decode_attn.cu | grep -n 'gfx906_attn_opt\\|STRATA_ATTN_OPT_DISPATCH\\|use_query_swizzle\\|STRATA_ATTN_OPT_SWZ' | head -40" % (R, PROD)))
print("=== 3. dispatch block context at PROD (around first gfx906_attn_opt) ===")
print(sh("git -C %s show %s:src/kernels/cuda/qsa_decode_attn.cu | sed -n '1095,1135p'" % (R, PROD)))
print(sh("git -C %s show %s:src/kernels/cuda/qsa_decode_attn.cu | sed -n '1155,1200p'" % (R, PROD)))

print("=== 4. who sets use_query_swizzle true (TUNED recipe) ===")
print(sh("git -C %s show %s:src/kernels/cuda/qsa_decode_attn.cu | grep -n 'use_query_swizzle\\|QUERY_SWIZZLE\\|GFX906_TUNED' | head -20" % (R, PROD)))
print(sh("grep -rn 'GFX906_ATTN_QUERY_SWIZZLE\\|QUERY_SWIZZLE' %s/src --include=*.cpp --include=*.hpp | head -15" % R))

print("=== 5. A2/A3 code shape at PROD: softmax shfl + sq/sp declarations ===")
print(sh("git -C %s show %s:src/kernels/cuda/qsa_decode_attn.cu | sed -n '25,45p'" % (R, PROD)))
print(sh("git -C %s show %s:src/kernels/cuda/qsa_decode_attn.cu | sed -n '132,145p'" % (R, PROD)))

print("=== 6. A1 router at PROD ===")
print(sh("git -C %s show %s:src/kernels/cuda/native_router.cu | sed -n '28,52p'" % (R, PROD)))
print(sh("git -C %s show %s:src/kernels/cuda/native_router.cu | sed -n '78,90p'" % (R, PROD)))

print("=== 7. A5 kv_q8 at PROD: dispatch macro state ===")
print(sh("git -C %s show %s:src/kernels/cuda/kv_q8.cu | grep -n 'STRATA_EXPERIMENTAL_SM60\\|STRATA_HIP_GFX906\\|Q8_GATHER8\\|pre75_q8_gather\\|wide' | head -25" % (R, PROD)))
