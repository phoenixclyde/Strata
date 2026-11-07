import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
src = open(r"D:/workbuddy_space/strata_ws/albus/r5/ab_p3.sh","rb").read().decode()
pl = base64.b64encode(src.encode()).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/ab_p3.sh && chmod +x /home/albus/strata166/tmp/ab_p3.sh && sh -n /home/albus/strata166/tmp/ab_p3.sh && echo SYNTAX_OK" % pl))
print(sh("ls -l /home/albus/strata166/data/gfx906-rocblas-5.5.0.txt"))
