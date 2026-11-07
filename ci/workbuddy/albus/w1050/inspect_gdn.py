#!/usr/bin/env python3
# W1050: R114 offline gate (GDN weight range) + R113 #30837 diff + fused_gdn code shape. Read-only.
import subprocess

R = "/home/albus/strata166/pr/k10"


def sh(cmd):
    r = subprocess.run(["bash", "-lc", cmd], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.stdout


print("=== 1. fused_gdn.cu: the bf16 dot sites (100-140) ===")
print(sh("sed -n '95,145p' %s/src/kernels/cuda/fused_gdn.cu" % R))

print("=== 2. fused_gdn weight/bias declarations ===")
print(sh("grep -n 'bf16\\|__hip_bfloat16\\|bfloat\\|half\\|w_a\\|w_b\\|w_c\\|w_g\\|weight\\|dot2\\|fmaf' %s/src/kernels/cuda/fused_gdn.cu | head -40" % R))

print("=== 3. GDN weight tensors in the model pack manifest ===")
print(sh("grep -i 'gdn\\|a_proj\\|b_proj\\|c_proj\\|g_proj\\|gating' /home/albus/strata166/models/native_experts.txt 2>/dev/null | head -20"))
print(sh("ls /home/albus/strata166/models/ /models/ 2>/dev/null | head -20"))
print(sh("find /home/albus/strata166/models /models -maxdepth 2 -name '*gdn*' -o -maxdepth 2 -name '*manifest*' -o -maxdepth 2 -name '*expert*' 2>/dev/null | head -15"))

print("=== 4. how GDN weights are loaded (host side) ===")
print(sh("grep -rn 'gdn' %s/src --include=*.cpp --include=*.hpp -l | head -10" % R))
print(sh("grep -rn 'A_bf16\\|gdn_a\\|gdn_w\\|GdnWeights\\|gdn.*bf16\\|bf16.*gdn' %s/src --include=*.cu --include=*.cpp --include=*.hpp | head -20" % R))

print("=== 5. mmq.cuh pin identity in our tree ===")
print(sh("cd %s && git log --oneline -2 -- third_party/ggml/src/ggml-cuda/mmq.cuh 2>/dev/null; ls third_party/ggml/src/ggml-cuda/mmq.cuh 2>/dev/null; grep -n '4c1004c\\|mmq.cuh' REBUILD_RECIPE.tsv 2>/dev/null | head" % R))
print(sh("find /home/albus/strata166/tmp/w1037/llama-master/ggml/src/ggml-cuda -name 'mmq.cuh' | head -2"))
