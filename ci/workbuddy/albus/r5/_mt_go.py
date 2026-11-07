import subprocess, base64
def sh(s, t=600):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
src = open(r"D:/workbuddy_space/strata_ws/albus/r5/multiturn_base.py","rb").read().decode()
pl = base64.b64encode(src.encode()).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/multiturn_base.py && wc -l /home/albus/strata166/tmp/multiturn_base.py" % pl, t=60))
print(sh("cd /home/albus/strata166/tmp && python3 multiturn_base.py 2>&1 | tail -20", t=560))
