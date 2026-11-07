import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
for loc, rm in [("albus/r5/mt_decode.py","/home/albus/strata166/tmp/mt_decode.py"),
                ("albus/r5/ab_p8.sh","/home/albus/strata166/tmp/ab_p8.sh")]:
    src=open(loc,"rb").read(); pl=base64.b64encode(src).decode("ascii")
    print(sh("echo '%s' | base64 -d > %s && wc -c %s" % (pl, rm, rm)).strip())
print(sh("chmod +x /home/albus/strata166/tmp/ab_p8.sh && sh -n /home/albus/strata166/tmp/ab_p8.sh && echo SYNTAX_OK"))
print(sh("curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 40; echo; ps -ef | grep -c '[a]b_p8'"))
