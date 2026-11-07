import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil
S = r'''
R=/home/albus/strata166/pr/k10
B=gfx906/attn-opt
for range in '1970,2088' '2330,2465' '2588,2630' '2810,2860' '3070,3100'; do
  echo "=== fused_gr.cu $range ==="
  git -C $R show $B:src/kernels/cuda/fused_gr.cu | sed -n "${range}p"
done

echo "=== fused_gr_bench CLI and modes ==="
git -C $R show $B:src/kernels/fused_gr_bench.cpp | grep -nE "argv|argc|usage|q8|variant|fast|bench|printf" | head -120

echo "=== gr_parity CLI ==="
git -C $R show $B:src/kernels/gr_parity.cpp | grep -nE "argv|argc|usage|q8|variant|fast|printf" | head -110

echo "=== existing cmake targets ==="
git -C $R grep -nE "fused_gr_bench|gr_parity" $B -- CMakeLists.txt src/kernels/CMakeLists.txt | head -40
'''
rc, out, err = _sshutil.run_remote(S, timeout=240)
print(out)
if err.strip(): print("ERR", err[-1000:])
raise SystemExit(rc)
