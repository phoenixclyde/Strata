import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
src=open("albus/r5/ab_p9.sh","rb").read(); pl=base64.b64encode(src).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/ab_p9.sh && chmod +x /home/albus/strata166/tmp/ab_p9.sh && sh -n /home/albus/strata166/tmp/ab_p9.sh && echo SYNTAX_OK" % pl, t=60))
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./ab_p9.sh > /tmp/ab_p9.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
