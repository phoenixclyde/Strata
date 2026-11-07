import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
for loc, rm in [("albus/r5/mt_phase.py","/home/albus/strata166/tmp/mt_phase.py"),
                ("albus/r5/ab_p8c.sh","/home/albus/strata166/tmp/ab_p8c.sh")]:
    src=open(loc,"rb").read(); pl=base64.b64encode(src).decode("ascii")
    print(sh("echo '%s' | base64 -d > %s && wc -c %s" % (pl, rm, rm)).strip())
print(sh("chmod +x /home/albus/strata166/tmp/ab_p8c.sh && sh -n /home/albus/strata166/tmp/ab_p8c.sh && echo SYNTAX_OK"))
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./ab_p8c.sh > /tmp/ab_p8c.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
