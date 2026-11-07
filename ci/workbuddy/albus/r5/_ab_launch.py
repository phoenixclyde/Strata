import subprocess, base64
HOST = "albus@192.168.50.166"
def sh(script, timeout=300):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=15",HOST,"base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8","replace")
src = open(r"D:/workbuddy_space/strata_ws/albus/r5/pf_ab.sh","rb").read().decode()
payload = base64.b64encode(src.encode()).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/pf_ab.sh && chmod +x /home/albus/strata166/tmp/pf_ab.sh && sh -n /home/albus/strata166/tmp/pf_ab.sh && echo SYNTAX_OK" % payload, timeout=120))
