import subprocess, base64, sys, time

HOST = "albus@192.168.50.166"


def sh(script, timeout=1200):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15", HOST,
                        "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


src = open(r"D:/workbuddy_space/strata_ws/albus/r5/pf_run.sh", "rb").read().decode()
payload = base64.b64encode(src.encode()).decode("ascii")
print(sh("mkdir -p /home/albus/strata166/tmp && echo '%s' | base64 -d > /home/albus/strata166/tmp/pf_run.sh && chmod +x /home/albus/strata166/tmp/pf_run.sh && echo PUSHED_OK" % payload))
print(sh("ls -l /home/albus/strata166/tmp/w776_bench.py && cd /home/albus/strata166/tmp && nohup setsid ./pf_run.sh > /tmp/pf_run.out 2>&1 < /dev/null & sleep 2; echo LAUNCHED"))
