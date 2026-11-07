import subprocess, base64
def sh(s, t=25):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./ab_p8.sh > /tmp/ab_p8.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
