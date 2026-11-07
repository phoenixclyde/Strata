import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

S = r'''
R=/home/albus/strata166/pr/k10
B=gfx906/attn-opt
echo "=== branch/source identity ==="
git -C $R rev-parse --short $B
git -C $R status --porcelain | wc -l

echo "=== qsa_pattn.cu: score functions and call sites ==="
git -C $R show $B:src/kernels/cuda/qsa_pattn.cu | grep -nE "dot8|dequant8|score_chunk|load_q_perm|launch|pattn|batch|__global__|template" | head -90

echo "=== qsa_prompt_attn.cu: score functions and call sites ==="
git -C $R show $B:src/kernels/cuda/qsa_prompt_attn.cu | grep -nE "dot8|dequant8|score_chunk|load_q_perm|launch|pattn|batch|__global__|template|fmaf" | head -110

echo "=== production dispatch: who calls qsa_pattn/qsa_prompt_attn ==="
git -C $R grep -nE "qsa_pattn|qsa_prompt_attn|prompt_attn_batch|pattn_mode" $B -- src/program src/prefill src/kernels | head -110

echo "=== qsa_pattn.cu 1-220 ==="
git -C $R show $B:src/kernels/cuda/qsa_pattn.cu | sed -n '1,220p'

echo "=== qsa_prompt_attn.cu 1-240 ==="
git -C $R show $B:src/kernels/cuda/qsa_prompt_attn.cu | sed -n '1,240p'
'''
rc, out, err = _sshutil.run_remote(S, timeout=240)
print(out)
if err.strip():
    print("ERR", err[-1000:])
raise SystemExit(rc)
