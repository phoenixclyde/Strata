import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil
S = r'''
R=/home/albus/strata166/pr/k10
B=gfx906/attn-opt

echo "=== fused_gr dispatch and defaults ==="
git -C $R show $B:src/kernels/cuda/fused_gr.cu | grep -nE "gr_down_(multi|v3|kernel)|gr_norm_multi|launch.*gr|fused_gr|q8_mixed|q8_xn|HC_Q8|GR_FAST|STRATA_QFUSE|down_v3|v3_on|persist" | tail -170

echo "=== fused_gr.cu 700-970 (v3 down) ==="
git -C $R show $B:src/kernels/cuda/fused_gr.cu | sed -n '700,970p'

echo "=== fused_gr.cu 1080-1450 (dispatch) ==="
git -C $R show $B:src/kernels/cuda/fused_gr.cu | sed -n '1080,1450p'

echo "=== fused_gr.hpp structures and API ==="
git -C $R show $B:include/strata/kernels/fused_gr.hpp | sed -n '1,260p'

echo "=== q8_mixed producers/consumers ==="
git -C $R grep -n "q8_mixed\|q8_xn" $B -- src include | head -100

echo "=== fused_gr tests/bench files ==="
git -C $R ls-tree -r --name-only $B | grep -E "fused_gr|gr_bench|gr_parity|hc_bench" | head -50
'''
rc, out, err = _sshutil.run_remote(S, timeout=300)
print(out)
if err.strip():
    print("ERR", err[-1000:])
raise SystemExit(rc)
