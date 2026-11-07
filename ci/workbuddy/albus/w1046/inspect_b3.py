import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

S = r'''
R=/home/albus/strata166/pr/k10
B=gfx906/attn-opt
P=/home/albus/strata166/pr/port-all

echo "=== B3 production source: dot8q / q8_1 mirror / callers ==="
git -C $R show $B:src/kernels/cuda/fused_gr.cu | grep -nE "dot8q|gr_q8_tail|q8_1|xn|__global__|down|HC|hc_|persist|fmaf" | head -150

echo "=== fused_gr.cu 1-330 ==="
git -C $R show $B:src/kernels/cuda/fused_gr.cu | sed -n '1,330p'

echo "=== fused_gr.cu 330-620 ==="
git -C $R show $B:src/kernels/cuda/fused_gr.cu | sed -n '330,620p'

echo "=== tests / parity / bench for fused_gr ==="
git -C $R ls-tree -r --name-only $B | grep -E "fused_gr|gr_.*(test|parity|bench)|hc_.*(test|parity|bench)" | head -50

echo "=== A1/A5 exact candidate diffs in port-all ==="
git -C $P diff e181bda5..HEAD -- src/kernels/cuda/native_router.cu src/kernels/cuda/kv_q8.cu | head -260

echo "=== B2 build guard and production fallback (exact lines) ==="
git -C $R show $B:src/kernels/cuda/qsa_pattn.cu | sed -n '25,62p'
git -C $R show $B:src/prefill/prefill.cpp | sed -n '4390,4440p'
'''
rc, out, err = _sshutil.run_remote(S, timeout=300)
print(out)
if err.strip():
    print("ERR", err[-1200:])
raise SystemExit(rc)
