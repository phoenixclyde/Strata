import subprocess, base64
def sh(s, t=115):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("cd /home/albus/strata166/tmp && python3 w776_bench.py M 1 2>&1 | grep -E 'run1'", t=110))
