import subprocess, base64
HOST = "albus@192.168.50.166"
def sh(script, timeout=120):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=15",HOST,"base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8","replace")
print(sh("cd /home/albus/strata166/tmp && setsid nohup ./pf_ab.sh > /tmp/pf_ab.out 2>&1 < /dev/null & sleep 3; echo LAUNCHED; ps -ef | grep -c '[p]f_ab.sh'", timeout=60))
