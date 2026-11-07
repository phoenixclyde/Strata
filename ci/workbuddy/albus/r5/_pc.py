import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("cat /home/albus/strata166/data/w792_prodchk.txt 2>/dev/null; echo ---; ps -ef | grep -c '[p]rodchk.sh'"))
