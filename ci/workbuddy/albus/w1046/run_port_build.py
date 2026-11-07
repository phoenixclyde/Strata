import os
import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1046"
R = "/home/albus/strata166/tmp/w1046"
for name in ("port_b3.py", "build_b3.sh"):
    ok, size, md5, detail = _sshutil.push_b64(os.path.join(W, name), R + "/" + name)
    print("push", name, ok, size, md5)
    if not ok:
        raise SystemExit(1)
prep = ("if [ -f /home/albus/strata166/pr/k10/src/kernels/cuda/fused_gr.cu.bak_w1046 ]; then "
        "mv /home/albus/strata166/pr/k10/src/kernels/cuda/fused_gr.cu.bak_w1046 " + R + "/fused_gr.cu.bak_w1046; fi")
rc, out, err = _sshutil.run_remote(prep, timeout=60)
if rc != 0:
    print(out, err)
    raise SystemExit(rc)
rc, out, err = _sshutil.run_remote("python3 " + R + "/port_b3.py", timeout=240)
print(out[-4000:])
if rc != 0:
    print("PORT ERR", err[-1500:])
    raise SystemExit(rc)
rc, out, err = _sshutil.run_remote("bash " + R + "/build_b3.sh", timeout=1800)
print(out[-5000:])
if err.strip():
    print("BUILD ERR", err[-1500:])
raise SystemExit(rc)
