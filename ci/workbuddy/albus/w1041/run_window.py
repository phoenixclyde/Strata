#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1041: push and run the four-arm R103 window (production is stopped for the GPU, then restored)."""
import os, sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1041"
for f, remote in (("window_r103.sh", "/home/albus/strata166/tmp/w1041/window_r103.sh"),
                  ("cmp_logits.py", "/home/albus/strata166/tmp/w1041/cmp_logits.py")):
    ok, size, md5, det = _sshutil.push_b64(os.path.join(W, f), remote)
    print("push", f, ok, size, md5)

rc, out, err = _sshutil.run_remote("bash /home/albus/strata166/tmp/w1041/window_r103.sh; echo EXIT=$?", timeout=1800)
print("rc=", rc)
print(out[-7000:])
if err.strip():
    print("STDERR:", err[-1500:])
