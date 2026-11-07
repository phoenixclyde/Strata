import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil
S = r'''
R=/home/albus/strata166/pr/k10
B=gfx906/attn-opt

echo "=== qsa_decode_attn.cu: V path, k8v4, OPT ==="
git -C $R show $B:src/kernels/cuda/qsa_decode_attn.cu | grep -nE "kv_mode|KV_MODE|v4|q4|acc\[|value|vdown|vup|fmaf|dequant|OPT|dp4a|dot8" | head -180

echo "=== qsa_decode_attn.cu score/value body 1-360 ==="
git -C $R show $B:src/kernels/cuda/qsa_decode_attn.cu | sed -n '1,360p'

echo "=== kv_q4.hpp layout ==="
git -C $R show $B:include/strata/kernels/kv_q4.hpp | sed -n '1,280p'

echo "=== kv_q4 implementation ==="
git -C $R show $B:src/kernels/cuda/kv_q4.cu | sed -n '1,300p' 2>/dev/null || true

echo "=== dot48 helper operand contract ==="
git -C $R show gfx906/dot48:include/strata/kernels/gfx906_dot.hpp | sed -n '1,180p'

echo "=== existing dot8/k8v4 ledger-relevant source comments ==="
git -C $R grep -nE "dot8|int4.*prob|prob.*int4|p.*int4|K100LC" $B -- src/kernels include/strata/kernels | head -100
'''
rc, out, err = _sshutil.run_remote(S, timeout=300)
print(out)
if err.strip(): print("ERR", err[-1200:])
raise SystemExit(rc)
