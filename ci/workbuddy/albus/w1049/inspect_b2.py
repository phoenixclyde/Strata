#!/usr/bin/env python3
# W1049: settle B2's real landing point + collect A1/A5 sites. Read-only.
import subprocess

R = "/home/albus/strata166/pr/k10"


def sh(cmd):
    r = subprocess.run(["bash", "-lc", cmd], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.stdout


print("=== 1. qsa_prompt_attn.cu gate region 2360-2520 ===")
print(sh("sed -n '2360,2520p' %s/src/kernels/cuda/qsa_prompt_attn.cu" % R))

print("=== 2. device/capability checks in qsa_prompt_attn.cu ===")
print(sh("grep -n 'cc\\|major\\|minor\\|arch\\|gfx\\|wmma\\|cp_async\\|mma_sync\\|refuse\\|trap\\|sm_\\|device' %s/src/kernels/cuda/qsa_prompt_attn.cu | head -70" % R))

print("=== 3. prefill.cpp dispatch (qsa_prompt / qsa_pattn / qsa_decode order) ===")
print(sh("grep -n 'qsa_prompt_attn\\|qsa_pattn_batch\\|qsa_decode_attn_batch\\|pattn_mode' %s/src/prefill/prefill.cpp | head -30" % R))
print(sh("grep -rn 'qsa_prompt_attn_batch' %s/src --include=*.cpp --include=*.cu --include=*.hpp | head -20" % R))

print("=== 4. production build: is qsa_prompt_attn.cu compiled? ===")
print(sh("grep -n 'qsa_prompt_attn' %s/build.ninja 2>/dev/null | head -10" % R))
print(sh("ls %s/build*/build.ninja /home/albus/strata166/build*/build.ninja 2>/dev/null | head" % R))

print("=== 5. symbols in live binary ===")
print(sh("docker exec strata166-407 sh -lc \"strings /data/bin/strata-0.1.57-hc4b | grep -c 'prompt_attn'\""))
print(sh("docker exec strata166-407 sh -lc \"strings /data/bin/strata-0.1.57-hc4b | grep 'prompt_attn\\|pattn' | head -12\""))

print("=== 6. A1 sites: native_router.cu 30-50 / 75-90 / 130-145 / 188-200 ===")
for a, b in ((30, 50), (75, 90), (130, 145), (188, 200)):
    print("--- %d-%d ---" % (a, b))
    print(sh("sed -n '%d,%dp' %s/src/kernels/cuda/native_router.cu" % (a, b, R)))

print("=== 7. A5 sites: kv_q8.cu 100-235 ===")
print(sh("sed -n '100,235p' %s/src/kernels/cuda/kv_q8.cu" % R))

print("=== 8. A3 sites: qsa_decode_attn.cu 25-45 + qsa_pattn 60-80 ===")
print(sh("sed -n '25,45p' %s/src/kernels/cuda/qsa_decode_attn.cu" % R))
print(sh("sed -n '60,80p' %s/src/kernels/cuda/qsa_pattn.cu" % R))

print("=== 9. production binary switch strings ===")
print(sh("docker exec strata166-407 sh -lc \"strings /data/bin/strata-0.1.57-hc4b | grep -o 'STRATA_GFX906_[A-Z0-9_]*' | sort -u\""))
