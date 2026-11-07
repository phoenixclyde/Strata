import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh('ls -l /home/albus/strata166/tmp/pf_run.sh 2>&1; ps -ef | grep -c "[p]f_run.sh"; ls -t /home/albus/strata166/data/r5_pf_*.txt 2>/dev/null | head -2; cat /tmp/pf_run.out 2>/dev/null | head -5'))
