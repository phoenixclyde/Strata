#!/usr/bin/env python3
"""Run a local shell script on 166 (scp + bash). Usage: rr.py <local_script> [timeout_s]"""
import subprocess
import sys
import os

HOST = "albus@192.168.50.166"
RDIR = "/home/albus/strata166/tmp/w1038"


def main():
    local = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    name = os.path.basename(local)
    remote = RDIR + "/" + name
    subprocess.run(["ssh", "-o", "ConnectTimeout=8", HOST, "mkdir -p " + RDIR], timeout=60)
    r = subprocess.run(["scp", "-q", local, HOST + ":" + remote], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print("SCP FAIL", r.stderr[:400])
        return 2
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", HOST, "bash " + remote],
                       capture_output=True, text=True, timeout=timeout)
    print(r.stdout)
    if r.stderr.strip():
        print("STDERR:", r.stderr[-1500:])
    print("RC=", r.returncode)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
