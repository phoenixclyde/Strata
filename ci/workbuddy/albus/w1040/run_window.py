#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: push and run the install window on 166 (this stops production: downtime starts inside)."""
import io, os, sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1040"
ok, size, md5, det = _sshutil.push_b64(os.path.join(W, "window_install.sh"),
                                      "/home/albus/strata166/tmp/w1040/window_install.sh")
print("push window:", ok, size, md5, det)
rc, out, err = _sshutil.run_remote(
    "bash /home/albus/strata166/tmp/w1040/window_install.sh; echo EXIT=$?", timeout=1500)
print("rc=", rc)
print(out[-6000:])
if err.strip():
    print("STDERR:", err[-2000:])
