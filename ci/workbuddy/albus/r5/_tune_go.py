import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
src = open(r"D:/workbuddy_space/strata_ws/albus/r5/tune.sh","rb").read().decode()
pl = base64.b64encode(src.encode()).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/tune/tune.sh && chmod +x /home/albus/strata166/tmp/tune/tune.sh && sh -n /home/albus/strata166/tmp/tune/tune.sh && echo SYNTAX_OK" % pl))
try:
    print(sh("cd /home/albus/strata166/tmp/tune && setsid nohup ./tune.sh >/tmp/tune.out 2>&1 </dev/null & echo LAUNCHED", t=20))
except subprocess.TimeoutExpired:
    print("LAUNCHED (ssh channel held, expected)")
