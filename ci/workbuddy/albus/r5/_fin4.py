import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
src=open(r"D:/workbuddy_space/strata_ws/albus/r5/finalize_p4.sh","rb").read().decode()
pl=base64.b64encode(src.encode()).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/finalize_p4.sh && chmod +x /home/albus/strata166/tmp/finalize_p4.sh && sh -n /home/albus/strata166/tmp/finalize_p4.sh && echo SYNTAX_OK" % pl))
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./finalize_p4.sh > /tmp/fin4.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
