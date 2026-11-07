#!/usr/bin/env python3
# W1049: extract A1/A5 port diffs + A4 build-flag mechanism. Read-only.
import subprocess

R = "/home/albus/strata166/pr/k10"
NEW = "91a7c5a4e284f71b44316927131248362802d0ef"   # port-all tip (A1/A5/pa6/pa7 content)
PROD = "03509d1b6895b4015f03a3aa416c962e5bf56d3d"  # production build sha


def sh(cmd):
    r = subprocess.run(["bash", "-lc", cmd], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.stdout


print("=== 1. native_router.cu diff PROD..NEW (A1) ===")
print(sh("git -C %s diff %s %s -- src/kernels/cuda/native_router.cu | head -220" % (R, PROD, NEW)))

print("=== 2. kv_q8.cu diff PROD..NEW (A5) ===")
print(sh("git -C %s diff %s %s -- src/kernels/cuda/kv_q8.cu | head -160" % (R, PROD, NEW)))

print("=== 3. qsa_decode_attn.cu diff stat (diag bits = pa6/pa7) ===")
print(sh("git -C %s diff --stat %s %s -- src/kernels/cuda/qsa_decode_attn.cu" % (R, PROD, NEW)))

print("=== 4. A5: does production k8v4 call the gather kernel? dispatch at PROD ===")
print(sh("git -C %s show %s:src/kernels/cuda/kv_q8.cu | sed -n '195,245p'" % (R, PROD)))

print("=== 5. A4: how are per-source flags passed in the 166 build? ===")
print(sh("ls /home/albus/strata166/build024/*.sh /home/albus/strata166/build024/*.ninja 2>/dev/null | head"))
print(sh("grep -rn 'amdgpu-sched\\|max-ilp\\|mllvm' /home/albus/strata166/build024/ /home/albus/strata166/tmp/w1039/ 2>/dev/null | head -10"))
print(sh("grep -n 'qsa_decode_attn.cu.o\\|fused_gr.cu.o\\|qsa_pattn.cu.o' /home/albus/strata166/build024/build.ninja 2>/dev/null | head -6"))

print("=== 6. what does bit2/bit4 do in the OPT template (A2/A3 scope) ===")
print(sh("git -C %s show %s:src/kernels/cuda/qsa_decode_attn.cu | grep -n 'OPT & 2\\|OPT & 4\\|LDS_PAD\\|warp_sum\\|warp_max\\|shfl_xor\\|dpp' | head -30" % (R, PROD)))
